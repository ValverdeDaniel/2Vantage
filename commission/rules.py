"""The split's rules (plan.md §5.6; H10, H19, H30; H.6 `rules.py`). Pure: the parties and settings come in as plain
data, and nothing here reads the database.

- `validate_rows(raw, parties)`: the editor's rows as the API takes them → (clean rows, errors keyed
  `rows.<i>.<field>`, `rows.primary` and `rows.split_total`). Exactly one appointed primary (a producer with a login
  counts as appointed, as the old picker did); each role takes only its kinds of party; a pool % total is at most 100
  and a gross % total under 100 (891f1b3 `commissions/services.py: validate_schedule_lines`, its words).
- `resolve`: the split that applies: the deal's, else the client's, else the deal owner, else the client owner, else
  the house at 100 % (H10).
- `producer_pct`: the primary's producer share in the year, else the firm default; the house keeps the rest.
- `year_number`: the year a deal pays in (H30, OQ72's default in §5.6's order): with earlier records, 1 + the number
  of distinct earlier effective years; else the typed "year with us"; else the first year for a deal opened for a
  Prospect or a New client, else unknown (renewal terms and a "year unknown" hole).
"""

from decimal import Decimal

from deals import comp as comps
from deals import lifecycle

from . import vocab

PICK_PRIMARY = 'Pick a primary producer'
ONE_PRIMARY = 'Only one primary producer'
PICK_PERSON = 'Pick a person'
TWICE = 'Listed twice'
UNKNOWN_ROLE = 'Unknown role'
BAD_ROW = 'Bad row'
PRIMARY_KIND = 'The primary producer must be a producer'
PRIMARY_APPOINTED = 'The primary producer must be appointed'
SECONDARY_KIND = 'A secondary producer must be one of our producers'
REFERRAL_KIND = 'A referral agent is an outside partner'
BAD_BASIS = 'Basis must be pool or gross'
NO_AMOUNT = 'Enter the split amount'
BAD_YEARS = 'Whole number of years (1 or more)'
POOL_OVER = 'Split percentages exceed 100 % of the producer share'
GROSS_OVER = 'Gross-basis percentages leave nothing for the house and producer'
HUNDRED = Decimal(100)


def party_key(raw):
    """('party', id) or ('user', id) for a row's person, or None. A producer with a login and no Party yet is named
    by `user` until the save creates the Party (H11)."""
    for name in ('party', 'user'):
        value = raw.get(name)
        if isinstance(value, bool):
            return None
        if isinstance(value, int) and value > 0:
            return (name, value)
        if isinstance(value, str) and value.isdigit() and int(value) > 0:
            return (name, int(value))
    return None


def canonical(key, person):
    """One key per person: a login that has a Party is named by the Party."""
    if person.get('id'):
        return ('party', person['id'])
    return ('user', person['user']) if person.get('user') else key


def clean_years(raw):
    """(a whole number of years 1–99 or None for blank, error)."""
    if raw in (None, ''):
        return None, None
    if isinstance(raw, bool):
        return None, BAD_YEARS
    try:
        years = int(str(raw).strip())
    except ValueError:
        return None, BAD_YEARS
    if years < 1 or years > vocab.LIMITS['max_years']:
        return None, BAD_YEARS
    return years, None


def _other_row(i, raw, person, role, errors, totals):
    """One secondary, split or referral row, cleaned; its errors under `rows.<i>.<field>`."""
    if role == vocab.SECONDARY and person['kind'] != vocab.PRODUCER:
        errors[f'rows.{i}.party'] = SECONDARY_KIND
    elif person['kind'] not in vocab.ROLE_KINDS[role]:
        errors[f'rows.{i}.party'] = REFERRAL_KIND
    basis = raw.get('basis') or vocab.POOL
    if basis not in vocab.BASIS_KEYS:
        errors[f'rows.{i}.basis'] = BAD_BASIS
        basis = vocab.POOL
    amount, error = comps.parse_comp(raw.get('amount'), allow_blank=True)
    if error:
        errors[f'rows.{i}.amount'] = error
    elif amount is None:
        errors[f'rows.{i}.amount'] = NO_AMOUNT
    elif amount['type'] == comps.PCT:
        totals[basis] += Decimal(amount['value'])
    renewal, error = comps.parse_comp(raw.get('renewal_amount'), allow_blank=True)
    if error:
        errors[f'rows.{i}.renewal_amount'] = error
    years, error = clean_years(raw.get('expires_after_years'))
    if error:
        errors[f'rows.{i}.expires_after_years'] = error
    return {
        'role': role,
        'amount': amount,
        'renewal_amount': renewal,
        'basis': basis,
        'expires_after_years': years,
        'works_it': bool(raw.get('works_it')) and role != vocab.REFERRAL,
    }


def validate_rows(raw_rows, parties):
    """(rows, errors). `parties` maps ('party', id) / ('user', id) to {kind, appointed, login, active}. Clean rows
    carry `party` or `user` (the id), the primary first and the others in the order given."""
    errors = {}
    if not isinstance(raw_rows, list) or not raw_rows:
        return [], {'rows.primary': PICK_PRIMARY}
    rows, seen, primaries = [], set(), 0
    totals = {vocab.POOL: Decimal(0), vocab.GROSS: Decimal(0)}
    for i, raw in enumerate(raw_rows):
        if not isinstance(raw, dict):
            errors[f'rows.{i}.party'] = BAD_ROW
            continue
        key = party_key(raw)
        person = parties.get(key) if key else None
        if person is None or not person.get('active', True):
            errors[f'rows.{i}.party'] = PICK_PERSON
            continue
        key = canonical(key, person)
        if key in seen:
            errors[f'rows.{i}.party'] = TWICE
            continue
        seen.add(key)
        role = raw.get('role') or vocab.SPLIT
        if role not in vocab.ROLE_KEYS:
            errors[f'rows.{i}.role'] = UNKNOWN_ROLE
            continue
        if role == vocab.PRIMARY:
            primaries += 1
            if person['kind'] != vocab.PRODUCER:
                errors[f'rows.{i}.party'] = PRIMARY_KIND
            elif not (person.get('login') or person.get('appointed')):
                errors[f'rows.{i}.party'] = PRIMARY_APPOINTED
            row = {'role': role, 'amount': None, 'renewal_amount': None, 'basis': vocab.POOL}
            row.update({'expires_after_years': None, 'works_it': False})
        else:
            row = _other_row(i, raw, person, role, errors, totals)
        rows.append({key[0]: key[1], **row})
    if primaries == 0:
        errors['rows.primary'] = PICK_PRIMARY
    elif primaries > 1:
        errors['rows.primary'] = ONE_PRIMARY
    if totals[vocab.POOL] > HUNDRED:
        errors['rows.split_total'] = POOL_OVER
    if totals[vocab.GROSS] >= HUNDRED:
        errors['rows.split_total'] = GROSS_OVER
    rows.sort(key=lambda row: 0 if row['role'] == vocab.PRIMARY else 1)
    return rows, errors


def resolve(deal_rows, client_rows, deal_owner, client_owner):
    """(source, rows): the deal's split, else the client's, else the deal owner (a party id or ('user', id)) as the
    primary, else the client owner, else the house alone (H10)."""
    if deal_rows:
        return vocab.DEAL, deal_rows
    if client_rows:
        return vocab.CLIENT, client_rows
    for source, owner in ((vocab.DEAL_OWNER, deal_owner), (vocab.CLIENT_OWNER, client_owner)):
        if owner is not None:
            return source, [{**owner, 'role': vocab.PRIMARY, 'amount': None, 'basis': vocab.POOL}]
    return vocab.HOUSE, []


def producer_pct(primary, settings, first_year):
    """(the producer's % of agency revenue, 'party' | 'default'): the primary's own figure for the year, else the
    firm default (Settings). `primary` is a dict with `first_year_pct` and `renewal_pct`, or None."""
    field = 'first_year_pct' if first_year else 'renewal_pct'
    own = (primary or {}).get(field)
    if own is not None:
        return Decimal(own), 'party'
    return Decimal(getattr(settings, field)), 'default'


def year_number(typed, opened_as, earlier=0):
    """The year the deal pays in: 1 + `earlier` (the client's distinct earlier effective years on records that are not
    void), else typed, else 1 unless the deal was opened for an Existing client (then None: not known, which pays the
    renewal terms)."""
    if earlier:
        return 1 + earlier
    if typed:
        return typed
    return None if opened_as == lifecycle.EXISTING_CLIENT else 1
