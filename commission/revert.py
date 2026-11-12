"""Revert of a commission Activity row (plan.md §3.7, O.3.2; H113): `activity.reverters['commission']`.

`deals.activity.revert` has already locked the Deal (when the row has one). This locks the rest in the services'
order (the Client, then commission's rows), refuses when a later write changed one of the row's keys (naming it), and
puts each key's "before" back: an agreed rate through `deals.values.apply`, the typed year, the deal's or the client's
split, a party's field, a firm default or the agency's rate (`deals.services.set_default_commission`), and a booked
record's typed facts, notes or shares (slice 49), each fact put back with the origin it had (`record_source:<id>`), so
a later booking refreshes it again. An owner the split set is its own `deal_facts` row, reverted on its own. A
booking (`booked`) follows the sale and refuses: un-sell, or Rebook, instead.
"""

from decimal import Decimal

from deals import activity, comp, values
from deals.models import AgencySettings, Client
from deals.services import set_default_commission

from . import book_rules
from . import terms as frozen
from .models import ClientSplit, Commission, Party, Record, Settings
from .services.booking import FOLLOWS_SALE

LABELS = {
    'year_number': 'The year with us',
    'split': 'The producers & splits',
    'rows': "The client's producers & splits",
    'first_year_pct': 'The first-year producer share',
    'renewal_pct': 'The renewal producer share',
    'confirmed': 'The confirmed defaults',
    'default_commission': "The agency's default rate",
    'default_split': 'The default split',
    'notes': 'The notes',
    'shares': 'The shares',
    'reason': 'The reason for the shares',
    'premium_annual': 'The premium',
    'rate': 'The rate',
    'employees': 'The enrolled count',
    'effective_date': 'The effective date',
    'term_end': 'The term end',
    'policy_number': 'The policy number',
}
PCTS = ('first_year_pct', 'renewal_pct')


def label(key):
    if key.startswith('rates.'):
        return f'The agreed rate on {key.removeprefix("rates.")}'
    return LABELS.get(key, key.replace('_', ' ').capitalize())


def _refuse(stale):
    stale = sorted(stale)
    return activity.changed_since([label(key) for key in stale], stale)


def _pct(value):
    return None if value is None else Decimal(str(value))


def _text(value):
    return format(value.normalize(), 'f') if isinstance(value, Decimal) else value


def _commission(pk, keys, user):
    row = Commission.objects.select_for_update().get(deal_id=pk)
    now = {key: _now_commission(row, key) for key in keys}
    stale = [key for key, (_b, after) in keys.items() if now[key] != after]
    if stale:
        raise _refuse(stale)
    rates = {key.removeprefix('rates.'): before or '' for key, (before, _a) in keys.items() if key.startswith('rates.')}
    values.apply(row.rates, row.sources, rates, values.source('typed', user))
    for key in ('year_number', 'split'):
        if key in keys:
            setattr(row, key, keys[key][0])
    row.updated_by = user
    row.save()


def _now_commission(row, key):
    return row.rates.get(key.removeprefix('rates.')) if key.startswith('rates.') else getattr(row, key)


def _client_split(pk, keys, user):
    Client.objects.select_for_update().only('id').get(pk=pk)
    row = ClientSplit.objects.select_for_update().filter(client_id=pk).first()
    before, after = keys['rows']
    if (row.rows if row else None) != after:
        raise _refuse(['rows'])
    if before is None:
        row.delete()
        return
    row.rows, row.updated_by = before, user
    row.save()


def _party(pk, keys, _user):
    party = Party.objects.select_for_update().get(pk=pk)
    stale = [key for key, (_b, after) in keys.items() if _text(getattr(party, key)) != after]
    if stale:
        raise _refuse(stale)
    for key, (before, _a) in keys.items():
        setattr(party, key, _pct(before) if key in PCTS else before)
    party.save(update_fields=[*keys, 'updated_at'])


def _settings(_pk, keys, _user):
    row = Settings.objects.select_for_update().get(pk=1)
    now = {key: _text(getattr(row, key)) for key in PCTS} | {'confirmed': row.confirmed_at is not None}
    stale = [key for key, (_b, after) in keys.items() if now[key] != after]
    if stale:
        raise _refuse(stale)
    for key in PCTS:
        if key in keys:
            setattr(row, key, _pct(keys[key][0]))
    if 'confirmed' in keys and not keys['confirmed'][0]:
        row.confirmed_at = row.confirmed_by = None
    row.save()


def _agency(_pk, keys, _user):
    before, after = keys['default_commission']
    stored = AgencySettings.objects.select_for_update().filter(pk=1).values_list('default_commission', flat=True)
    now, _error = comp.parse_comp(stored.first(), allow_blank=True)
    if now != after:
        raise _refuse(['default_commission'])
    set_default_commission(before)


def _record_now(record, merged, key):
    if key == 'notes':
        return record.notes
    if key in ('shares', 'reason'):
        return (record.terms or {}).get(key)
    return merged.get(key)


def _record(pk, keys, user, origins):
    """A record's typed facts, notes or shares put back; each fact with the origin it had before it was typed."""
    record = Record.objects.select_for_update().get(pk=pk)
    merged = book_rules.facts(record)
    stale = [key for key, (_b, after) in keys.items() if (_record_now(record, merged, key) or None) != (after or None)]
    if stale:
        raise _refuse(stale)
    facts = {key: before if before is not None else '' for key, (before, _a) in keys.items() if key in FACTS}
    values.apply(merged, record.sources, facts, lambda key: values.source(origins.get(key) or 'typed', user))
    book_rules.split_facts(record, merged)
    if 'notes' in keys:
        record.notes = keys['notes'][0] or ''
    if 'shares' in keys or 'reason' in keys:
        record.terms = {**(record.terms or {}), **{k: keys[k][0] for k in ('shares', 'reason') if k in keys}}
        record.party_ids = frozen.party_ids(record.terms)
    record.updated_by = user
    record.save()


FACTS = book_rules.COLUMNS + book_rules.VALUES

PUT_BACK = {
    'commission': _commission,
    'client_split': _client_split,
    'party': _party,
    'settings': _settings,
    'agency': _agency,
}


def _flipped(entry):
    return activity.change(entry['t'], {key: [after, before] for key, (before, after) in entry['k'].items()})


def revert(row, user):
    if row.action == 'booked':
        raise activity.Refused(FOLLOWS_SALE)
    later = activity.later_keys(row)
    if later:
        raise _refuse([key for _target, key in later])
    # The services' lock order: the Deal (locked by deals.activity), the Client, then commission's rows.
    order = ['client_split', 'commission', 'party', 'settings', 'agency', 'record', 'record_source']
    origins = {
        entry['t'].partition(':')[2]: {key: pair[0] for key, pair in entry['k'].items()}
        for entry in row.changes
        if entry['t'].startswith('record_source:') and isinstance(entry['k'], dict)
    }
    written = []
    for entry in sorted(row.changes, key=lambda entry: order.index(entry['t'].partition(':')[0])):
        kind, _, pk = entry['t'].partition(':')
        if kind not in (*PUT_BACK, 'record', 'record_source') or not isinstance(entry['k'], dict):
            raise activity.Refused(activity.NO_REVERTER)
        if kind == 'record':
            _record(int(pk), entry['k'], user, origins.get(pk, {}))
        elif kind != 'record_source':
            PUT_BACK[kind](int(pk), entry['k'], user)
        written.append(_flipped(entry))
    return written
