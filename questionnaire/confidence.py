"""The questionnaires' part of the Overview's data confidence (plan.md §8.6, §3.8; M83, M90, M91; M.6 "questionnaire:
counts and marked rows with `value: null`"; slice 64): what review's `selectors.confidence` reads from the deal's
forms.

- `source_counts(deal_id)`: the answers stored on every form, counted by what the review rules read (one query); a
  live prefill is not stored, so it counts only once a person confirmed it (G27);
- `marked(deal_id, cap)`: the answers marked ⚑ Needs checking or Ignored, newest first, at most `cap` of each, named
  by the form and the question, and never with the answer: no value is read (`value` is None), as a medical answer
  is member data (§3.8).
Reads only.
"""

from documents import source_counts as counts

from . import forms
from .models import Questionnaire
from .services.answers import label_of

OWNER = 'questionnaire'


def _forms(deal_id):
    return Questionnaire.objects.filter(deal_id=deal_id)


def source_counts(deal_id):
    return counts.grouped(_forms(deal_id), values='answers')


def marked(deal_id, cap):
    out = []
    for row in counts.marked(_forms(deal_id), cap, columns=('form',), values='answers'):  # hidden=None: none read
        (form_key,) = row.columns
        form = forms.FORMS.get(form_key)
        out.append(
            {
                'ref': f'questionnaire:{form_key}:{row.key}',
                'owner': OWNER,
                'state': row.state,
                'at': row.at,
                'by': row.by,
                'doc': row.doc,
                'where': forms.label(form_key) or 'Questionnaire',
                'label': label_of(form, row.key) if form else row.key,
                'value': None,
                'tab': 'questionnaire',
                'form': form_key,
            }
        )
    return out
