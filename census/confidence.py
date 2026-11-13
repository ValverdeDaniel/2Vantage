"""census's part of the Overview's data confidence (plan.md §8.6, §3.8; M83, M90, M91; M.5 B1; slice 64): what
review's `selectors.confidence` reads from the roster.

- `source_counts(deal_id)`: the live people's stored values counted by what the review rules read (one query);
- `marked(deal_id, cap)`: the cells marked ⚑ Needs checking or Ignored, newest first, at most `cap` of each, each
  named by its row and column ("Census · Employee row 3", "Date of birth") and never by the person: no value is read
  at all (`value` is None), so no name, birth date or SSN can reach the Overview (§3.8; the old app's PHI rule).
Reads only.
"""

from documents import source_counts as counts

from . import fields
from .models import Member

OWNER = 'census'
KIND_WORDS = {fields.EMPLOYEE: 'Employee', fields.DEPENDENT: 'Dependent'}


def _people(deal_id):
    return Member.objects.filter(deal_id=deal_id)


def source_counts(deal_id):
    return counts.grouped(_people(deal_id))


def marked(deal_id, cap):
    out = []
    for row in counts.marked(_people(deal_id), cap, columns=('kind', 'position')):  # hidden=None: no value read
        kind, position = row.columns
        out.append(
            {
                'ref': f'census:{row.row_id}:{row.key}',
                'owner': OWNER,
                'state': row.state,
                'at': row.at,
                'by': row.by,
                'doc': row.doc,
                'where': f'Census · {KIND_WORDS.get(kind, "Person")} row {position + 1}',
                'label': fields.label(row.key),
                'value': None,
                'tab': 'census',
            }
        )
    return out
