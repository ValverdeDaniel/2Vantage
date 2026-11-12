"""The deal's agreed rates and the typed "year with us" (plan.md §5.6, §7.10; H5, H30): `update`.

Any deal user may edit a rate (D-011: producers set it at RFP time). Each line is one key, merged under the row's lock,
so two people editing two lines never erase each other (bug 17); a rate goes through `deals.values.apply` with its
own `sources` entry. Locks the Deal first, then the Commission row (created on the first write). One Activity row per
call, coalesced while one person keeps editing (`commission:rates:<deal>`).
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, lines, values
from deals import comp as comps
from deals.models import Deal

from .. import rules
from ..models import Commission

AREA = 'commission'
FIELDS = ('rates', 'year_number')
Updated = namedtuple('Updated', 'changed activity')


def target(deal_id):
    return f'commission:{deal_id}'


def commission_row(deal):
    """The deal's Commission, locked, or a new unsaved one: a row is created only by a write that changes it."""
    return Commission.objects.select_for_update().filter(deal_id=deal.id).first() or Commission(deal=deal)


def clean(changes):
    """({line: Comp | ''}, year or None, whether the year was sent); 400 with every error at once."""
    if not isinstance(changes, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    errors, rates = {}, {}
    for key in set(changes) - set(FIELDS):
        errors[key] = ['Not a commission field.']
    raw = changes.get('rates', {})
    if not isinstance(raw, dict):
        errors['rates'] = ['Send the rates as {line: rate}.']
        raw = {}
    for line, value in raw.items():
        if line not in lines.BY_KEY:
            errors[f'rates.{line}'] = ['Not a line.']
            continue
        found, error = comps.parse_comp(value, allow_blank=True)
        if error:
            errors[f'rates.{line}'] = [error]
        else:
            rates[line] = found or ''
    year, error = rules.clean_years(changes.get('year_number'))
    if error:
        errors['year_number'] = [error]
    if errors:
        raise ValidationError(errors)
    return rates, year, 'year_number' in changes


@transaction.atomic
def update(user, deal_id, changes):
    """Set any of the agreed rates (`{line: Comp | '' to clear}`) and the year. Returns Updated({key: [before,
    after]}, Activity | None); an unchanged value writes nothing, not even its source (§3.7)."""
    rates, year, has_year = clean(changes)
    deal = values.locked(Deal, deal_id)
    row = commission_row(deal)
    diff = values.apply(row.rates, row.sources, rates, values.source('typed', user))
    keyed = {f'rates.{line}': pair for line, pair in diff.items()}
    if has_year and row.year_number != year:
        keyed['year_number'] = [row.year_number, year]
        row.year_number = year
    if not keyed:
        return Updated({}, None)
    row.updated_by = user
    row.save()
    noun = 'agreed rate' if 'year_number' not in keyed else 'commission value'
    entry = activity.record(
        deal,
        user,
        AREA,
        'updated',
        'Edited',
        count=len(keyed),
        coalesce_key=f'commission:rates:{deal.id}',
        noun=noun,
        changes=[activity.change(target(deal.id), keyed)],
    )
    return Updated(keyed, entry)
