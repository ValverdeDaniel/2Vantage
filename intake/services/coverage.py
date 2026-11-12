"""Current coverage rows: add, edit and remove (plan.md §6.5, §7.6; B14, B19; OQ15).

One service behind both editors: the Current coverage subcards and the intent card's Current plan cells, its
"＋ Add a line…" and its note and guarantee inputs. The intent card's two controls (in force, this year) and its ×
go through `intent.set_intent`, because they also write the lines to quote.

Once a line has current plans in the Advisor, its carrier and funding come from the plans, read-only (§6.5): a write
of either answers 400 with the sentence below. Ported from old Vantage 891f1b3 `views/market.py`
(`_clean_coverage_line_data`, `CoverageLineCreateView`, `CoverageLineDetailView`).
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, comp, lines

from .. import coverage, providers, values
from ..models import CurrentCoverage
from . import rows

FROM_PLANS = 'Edit carrier and funding on the current plans in the Advisor.'
TEXT = {'carrier': 200, 'notes': 300}
BOOLS = ('in_force', 'on_proposal')
FUNDING = {key for key, _ in lines.FUNDING}

Written = namedtuple('Written', 'row changed activity')  # changed: {field: [before, after]}; activity: the row or None


def clean(data, line_has_plans=False):
    """The coverage fields of a request, checked. 400 with every refusal at once; unknown keys are ignored."""
    cleaned, errors = {}, {}
    if 'line' in data:
        line = str(data['line'] or '').strip()
        if line not in lines.BY_KEY:
            errors['line'] = ['Unknown line of coverage.']
        cleaned['line'] = line
    for key, limit in TEXT.items():
        if key in data:
            text = str(data[key] if data[key] is not None else '').strip()
            if len(text) > limit:
                errors[key] = [f'Keep it under {limit} characters.']
            cleaned[key] = text
    if 'funding' in data:
        funding = str(data['funding'] or '').strip()
        if funding and funding not in FUNDING:
            errors['funding'] = ['Unknown funding type.']
        cleaned['funding'] = funding
    if line_has_plans:
        for key in ('carrier', 'funding'):
            if key in data:
                errors[key] = [FROM_PLANS]
    for key in BOOLS:
        if key in data:
            if not isinstance(data[key], bool):
                errors[key] = ['Send true or false.']
            cleaned[key] = bool(data[key])
    for key in rows.DATES:
        if key in data:
            raw = str(data[key] or '').strip()
            parsed = values.parse_date(raw) if raw else None
            if raw and parsed is None:
                errors[key] = [f'Could not read "{raw}" as a date.']
            cleaned[key] = parsed
    if 'commission' in data:
        parsed, error = comp.parse_comp(data['commission'])
        if error:
            errors['commission'] = [error]
        cleaned['commission'] = parsed or {}
    if 'commission_source' in data:
        source = str(data['commission_source'] or '').strip()
        if source and source not in coverage.COMMISSION_SOURCE_KEYS:
            errors['commission_source'] = ['Unknown source.']
        cleaned['commission_source'] = source
    if errors:
        raise ValidationError(errors)
    return cleaned


def has_plans(deal_id, line):
    """Whether the line has current plans in the Advisor (quotes' provider)."""
    return bool((providers.quote_lines(deal_id).get(line) or {}).get('current'))


def _record(deal, user, action, summary, changes, coalesce=False):
    return activity.record(
        deal,
        user,
        rows.AREA,
        action,
        summary,
        changes=changes,
        coalesce_key='intake:coverage' if coalesce else '',
        noun='coverage value' if coalesce else '',
    )


@transaction.atomic
def create_coverage(user, deal_id, data):
    """A new row (B14's ＋ Add coverage line; B19's ＋ Add a line…, sent with in_force false)."""
    deal = rows.lock_deal(deal_id)
    if 'line' not in data:
        raise ValidationError({'line': ['Choose the line of coverage.']})
    cleaned = clean(data, has_plans(deal_id, str(data.get('line') or '')))
    row = CurrentCoverage.objects.create(deal=deal, sort_order=rows.next_sort_order(deal_id), **cleaned)
    label = lines.label(row.line)
    row_activity = _record(deal, user, 'coverage', f'Added a coverage line: {label}', [
        activity.change(rows.target(row.id), rows.created(row))
    ])
    return Written(row, rows.created(row), row_activity)


@transaction.atomic
def update_coverage(user, coverage_id, data):
    """Edit one row; an unchanged value writes nothing, not even Activity."""
    deal_id = CurrentCoverage.objects.values_list('deal_id', flat=True).get(pk=coverage_id)
    deal = rows.lock_deal(deal_id)
    row = rows.lock_coverage(deal_id, [coverage_id])[0]
    cleaned = clean(data, has_plans(deal_id, str(data.get('line') or row.line)))
    before = rows.state(row)
    for key, value in cleaned.items():
        setattr(row, key, value)
    changed = rows.changed(before, row)
    if not changed:
        return Written(row, {}, None)
    row.save(update_fields=[key for key in cleaned if key in changed])
    entry = [activity.change(rows.target(row.id), changed)]
    return Written(row, changed, _record(deal, user, 'coverage', 'Edited', entry, coalesce=True))


@transaction.atomic
def delete_coverage(user, coverage_id):
    """Remove one row (the subcard's ×). The lines to quote stay: the card's × removes a whole line (set_intent)."""
    deal_id = CurrentCoverage.objects.values_list('deal_id', flat=True).get(pk=coverage_id)
    deal = rows.lock_deal(deal_id)
    row = rows.lock_coverage(deal_id, [coverage_id])[0]
    before = rows.state(row)
    row.delete()
    summary = f'Removed a coverage line: {lines.label(before["line"])}'
    entry = [activity.change(rows.target(coverage_id), rows.removed(before))]
    return Written(None, rows.removed(before), _record(deal, user, 'coverage', summary, entry))
