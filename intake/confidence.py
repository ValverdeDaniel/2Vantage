"""intake's part of the Overview's data confidence (plan.md §8.6; M83, M90, M91; slice 64): what review's
`selectors.confidence` reads from the deal's Intake row (there is at most one; a deal with none counts nothing).

- `source_counts(deal_id)`: the answers stored, counted by what the review rules read (one query);
- `marked(deal_id, cap)`: the answers marked ⚑ Needs checking or Ignored, newest first, at most `cap` of each, named
  "Intake" and by the question, with the answer (company facts, never member data).
Reads only.
"""

import json

from documents import source_counts as counts

from . import form
from .models import Intake

OWNER = 'intake'


def _rows(deal_id):
    return Intake.objects.filter(deal_id=deal_id)


def _shown(text):
    """A multi question's answer (a list, read back as JSON text) as its choices joined; anything else as it is."""
    if text and text.startswith('['):
        try:
            return ', '.join(str(item) for item in json.loads(text))
        except ValueError:
            return text
    return text


def source_counts(deal_id):
    return counts.grouped(_rows(deal_id), values='answers')


def marked(deal_id, cap):
    return [
        {
            'ref': f'intake:{row.key}',
            'owner': OWNER,
            'state': row.state,
            'at': row.at,
            'by': row.by,
            'doc': row.doc,
            'where': 'Intake',
            'label': form.BY_KEY[row.key]['label'] if row.key in form.BY_KEY else row.key,
            'value': _shown(row.value),
            'tab': 'intake',
        }
        for row in counts.marked(_rows(deal_id), cap, hidden=(), values='answers')
    ]
