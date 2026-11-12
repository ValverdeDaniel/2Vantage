"""Applying Claude's re-check (plan.md §10.4, §10.7; D93, E77, OQ28; slice 22): what a person ticked on the re-check
card, written through quotes' own writers in one transaction that locks the Deal, then the plans by id (O.3.7).

- **Fixes** (`set_values`) land as a read's values do (`read_plans.Landing`): Claude's value with its file and page,
  only while the plan still holds what Claude checked (else said and left), never on a sold plan; one Activity row
  (area `quote_read`), whose Revert puts back the flagged value with its source as it was.
- **Approvals** (`confirm`) go through `review.mark_values` as the person who pressed Apply, with `via: recheck`
  (E77, Ch. 3): one `marked` row. Claude never approves a value itself (D-119): this runs only from Apply.
The job keeps both rows (`activity_ids`), so ↶ Undo this run reverts them together (`revert_read.undo`). Returns the
`landed` record, as a read's apply does.
"""

from django.db import transaction

from deals import activity

from .. import fields, signals
from ..models import Plan
from ..reader import choice
from . import locks
from .read_apply import AREAS
from .read_plans import Landing, label_of
from .review import mark_values

AREA, ACTION = 'quote_read', 'recheck'
GONE = '{plan}: no longer on the table, so nothing was written to it.'
CHANGED = '{plan}: {label} changed since the re-check, so it was left as it is.'
SOLD = '{plan} is sold, so {label} stays as sold.'
NOTHING = 'Nothing changed: the values were already as the re-check proposed.'


def _words(fixed, approved):
    parts = []
    if approved:
        parts.append(f'approved {approved} value{"s" if approved != 1 else ""}')
    if fixed:
        parts.append(f'fixed {fixed} value{"s" if fixed != 1 else ""}')
    return ' · '.join(parts)


@transaction.atomic
def apply(user, deal, job, select=None, picks=None):
    chosen = [
        entry for entry in choice.choose(job.result or {}, select) if entry.item['op'] in ('confirm', 'set_values')
    ]
    deal = locks.deal(deal.id)
    ids = sorted({entry.item['plan'] for entry in chosen})
    plans = {plan.id: plan for plan in Plan.objects.select_for_update().filter(deal=deal, id__in=ids).order_by('id')}
    landing = Landing(user, deal, plans, job)
    refs, skipped = [], []
    for entry in chosen:
        item = entry.item
        plan = plans.get(item['plan'])
        if plan is None:
            skipped.append(GONE.format(plan=f'{item["carrier"]} {item["name"]}'))
            continue
        for value in entry.values:
            label = fields.BY_KEY.get(value['key'], {}).get('label', value['key'])
            if item['op'] == 'confirm' and str(plan.values.get(value['key']) or '') != str(value['old'] or ''):
                skipped.append(CHANGED.format(plan=label_of(plan), label=label))
            elif item['op'] == 'confirm':
                refs.append(f'plan:{plan.id}:{value["key"]}')
            elif plan.sold:
                skipped.append(SOLD.format(plan=label_of(plan), label=label))
        if item['op'] == 'set_values' and not plan.sold:
            landing.land(entry)  # only while the plan still holds what Claude checked (else said: `skipped`)
    entries = landing.entries()
    rows = []
    if entries:
        count = sum(len([k for k in entry['k'] if k in fields.BY_KEY]) for entry in entries)
        rows.append(
            activity.record(
                deal,
                user,
                AREA,
                ACTION,
                f'Fixed {count} plan value{"s" if count != 1 else ""} from Claude’s re-check',
                changes=entries,
            )
        )
        signals.changed(deal.id, {plans[int(entry['t'].partition(':')[2])].line for entry in entries})
    marked = mark_values(user, deal, 'approve', refs=refs, via='recheck') if refs else None
    if marked is not None and marked.row is not None:
        rows.append(marked.row)
    fixed = sum(len([k for k in diff if k in fields.BY_KEY]) for diff in landing.diffs.values())
    approved = len(marked.values) if marked is not None else 0
    plan_ids = sorted({*landing.diffs, *(plan.id for plan, _key in (marked.values if marked else []))})
    return {
        'activity_id': rows[0].id if rows else None,
        'activity_ids': [row.id for row in rows],
        'plan_ids': plan_ids,
        'created': [],
        'areas': AREAS if rows else [],
        'summary': _words(fixed, approved) or NOTHING,
        'skipped': skipped + landing.skipped,
        'sources': landing.sources,
        'layouts': {},
    }
