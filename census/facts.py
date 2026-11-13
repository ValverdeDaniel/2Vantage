"""The census's stored counts (plan.md §5.3.5, §5.3.6, §6.6; O.3.7, OQ9 c; Q.3 #9).

`compute(deal_id)` works the counts out from the live people's approved values: employees, dependents, validation
errors and warnings, required cells (total, filled, and blanks by column), pending client answers and people, the
rollup (`census.rollup.compute`) and the last import's time. `refresh(deal_id)` stores them in `CensusFacts` inside
the caller's transaction, after the census rows it wrote (lock order: the Deal, then census rows; O.3.7); an equal
answer writes nothing. A deal with no census and no row stays without one. `differences` and `check` compare the
stored row with a rebuild (`manage.py rebuild_facts`).

What requiredness reads of the deal — its lines to quote and whether medical is in force — is intake's; intake's
writes announce a change through `intake.signals.coverage_changed`, which census answers with `refresh` (O.1).
Readiness: filled ÷ total, rounded, 100 when nothing is required, at most 99 while an error is open. Census OK: an
employee, no missing required cell and no error.
"""

from django.db.models import Max

from deals import batch, clock
from deals.models import Deal
from intake.models import CurrentCoverage

from . import fields, providers, rollup, validation
from .models import PERSON, CensusFacts, CensusImport, CensusSettings, Member

COUNTS = (
    'employees',
    'dependents',
    'errors',
    'warnings',
    'required_total',
    'required_filled',
    'missing',
    'pending_answers',
    'pending_people',
    'rollup',
    'last_import_at',
)


def context(deal):
    """What requiredness reads of the deal (fields.Context)."""
    in_force = CurrentCoverage.objects.filter(deal_id=deal.id, line='medical', in_force=True).exists()
    return fields.Context(list(deal.requested_lines or []), in_force)


def people(deal_id):
    """The live people as plain dicts (one query): what validation, requiredness and the rollup read."""
    wanted = ('id', 'kind', 'employee_id', 'position', 'values', 'sources', 'client')
    return list(Member.objects.filter(deal_id=deal_id).values(*wanted))


def _pending(entry):
    return isinstance(entry, dict) and entry.get('status') == 'pending'


def needed(deal):
    """{kind: the keys required of that kind of person} on this deal (fields.is_required, once per kind)."""
    ctx = context(deal)
    rules = CensusSettings.objects.filter(deal_id=deal.id).values_list('rules', flat=True).first() or {}
    carrier = providers.carrier_required(deal.id)
    return {kind: fields.required_keys(kind, ctx, rules, carrier) for kind, _ in fields.KINDS}


def missing_keys(person, keys):
    """The required keys a person leaves blank. A slot with a pending client answer is not missing (L.6)."""
    client = person.get('client') or {}
    return [key for key in keys if not person['values'].get(key) and not _pending(client.get(key))]


def required(found, keys):
    """(total, filled, {key: blanks}) over the people, with `keys` from `needed`."""
    total = filled = 0
    missing = {}
    for person in found:
        wanted = keys[person['kind']]
        blanks = missing_keys(person, wanted)
        total += len(wanted)
        filled += len(wanted) - len(blanks)
        for key in blanks:
            missing[key] = missing.get(key, 0) + 1
    return total, filled, missing


def compute(deal_id):
    """The counts as they should be stored now."""
    deal = Deal.objects.only('id', 'requested_lines').get(pk=deal_id)
    found = people(deal_id)
    total, filled, missing = required(found, needed(deal))
    errors, warnings = validation.counts(validation.validate(found, clock.today()))
    pending_people = Member.all_objects.filter(
        deal_id=deal_id,
        removed_at__isnull=True,
        added_by_link__isnull=False,
        client__contains={PERSON: {'status': 'pending'}},
    ).count()
    last = CensusImport.objects.filter(deal_id=deal_id, status=CensusImport.APPLIED).aggregate(at=Max('applied_at'))
    return {
        'employees': sum(1 for person in found if person['kind'] == fields.EMPLOYEE),
        'dependents': sum(1 for person in found if person['kind'] == fields.DEPENDENT),
        'errors': errors,
        'warnings': warnings,
        'required_total': total,
        'required_filled': filled,
        'missing': missing,
        'pending_answers': sum(
            1
            for person in found
            for key, entry in (person.get('client') or {}).items()
            if key != PERSON and _pending(entry)
        ),
        'pending_people': pending_people,
        'rollup': rollup.compute(found),
        'last_import_at': last['at'],
    }


EMPTY = {
    **dict.fromkeys(COUNTS, 0),
    'missing': {},
    'rollup': rollup.compute([]),
    'last_import_at': None,
}


def _stored(ids):
    return {row.pop('deal_id'): row for row in CensusFacts.objects.filter(deal_id__in=ids).values('deal_id', *COUNTS)}


def stored(deal_id):
    """The stored counts (one query, or one for a whole batch scope; `deals.batch`), else the empty counts."""
    row = batch.per_deal('census.stored', deal_id, _stored)
    return dict(row) if row else dict(EMPTY)


def refresh(deal_id):
    """Rewrite the deal's CensusFacts when its counts changed, in the caller's transaction. Returns the fields that
    changed."""
    data = compute(deal_id)
    row = CensusFacts.objects.select_for_update().filter(deal_id=deal_id).first()
    if row is None:
        if data == EMPTY:
            return []
        CensusFacts.objects.create(deal_id=deal_id, **data)
        return list(COUNTS)
    changed = [key for key in COUNTS if getattr(row, key) != data[key]]
    if changed:
        for key in changed:
            setattr(row, key, data[key])
        row.save(update_fields=[*changed, 'updated_at'])
    return changed


def differences(deal_id):
    """{field: (stored, rebuilt)} where the stored counts differ from a rebuild."""
    have, want = stored(deal_id), compute(deal_id)
    return {key: (have[key], want[key]) for key in COUNTS if have[key] != want[key]}


def readiness(counts):
    total, filled = counts['required_total'], counts['required_filled']
    pct = round(filled / total * 100) if total else 100
    return min(pct, 99) if counts['errors'] else pct


def summary(counts):
    """The census summary (§5.3.5) from stored counts."""
    missing = counts['required_total'] - counts['required_filled']
    return {
        'employees': counts['employees'],
        'dependents': counts['dependents'],
        'errors': counts['errors'],
        'warnings': counts['warnings'],
        'required_total': counts['required_total'],
        'required_filled': counts['required_filled'],
        'missing_required': missing,
        'readiness_pct': readiness(counts),
        'ok': counts['employees'] > 0 and missing == 0 and counts['errors'] == 0,
    }


def state(deal_id):
    """intake.providers.census_state: {has_roster, employees, errors, ok} (B33, C23), one query."""
    found = summary(stored(deal_id))
    has_roster = found['employees'] + found['dependents'] > 0
    return {'has_roster': has_roster, 'employees': found['employees'], 'errors': found['errors'], 'ok': found['ok']}


def deal_ids():
    """Every deal with census facts or people: what `rebuild_facts` checks."""
    with_rows = set(CensusFacts.objects.values_list('deal_id', flat=True))
    return sorted(with_rows | set(Member.all_objects.values_list('deal_id', flat=True).distinct()))
