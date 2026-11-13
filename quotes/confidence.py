"""quotes' part of the Overview's data confidence (plan.md §8.6; M83, M86, M87, M90, M91; M.6 "quotes: `source_counts`
and marked rows as SQL aggregates"; slice 64): what review's `selectors.confidence` reads from the plans.

- `source_counts(deal_id)`: the live plans' stored values counted by what the review rules read (one query);
- `marked(deal_id, cap)`: the plan values marked ⚑ Needs checking or Ignored, newest first, at most `cap` of each, each
  named by its plan ("Carrier — Plan") and field, with its value — never a laser's (a key-only value, §3.8).
Reads only.
"""

from deals import activity
from documents import source_counts as counts

from . import fields
from .models import Plan

OWNER = 'quotes'


def _plans(deal_id):
    return Plan.objects.filter(deal_id=deal_id)


def source_counts(deal_id):
    return counts.grouped(_plans(deal_id))


def marked(deal_id, cap):
    out = []
    hidden = sorted(activity.key_only_values)  # lasers: their key only, never the value
    for row in counts.marked(_plans(deal_id), cap, columns=('carrier', 'name'), hidden=hidden):
        carrier, name = row.columns
        out.append(
            {
                'ref': f'plan:{row.row_id}:{row.key}',
                'owner': OWNER,
                'state': row.state,
                'at': row.at,
                'by': row.by,
                'doc': row.doc,
                'where': ' — '.join(part for part in (carrier, name) if part),
                'label': fields.BY_KEY[row.key]['label'] if row.key in fields.BY_KEY else row.key,
                'value': None if row.key in hidden else row.value,
                'tab': 'advisor',
            }
        )
    return out
