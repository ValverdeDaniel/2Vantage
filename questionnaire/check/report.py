"""The check of one form on a deal: `GET …/questionnaires/{form}/check/` (plan.md §7.9; G64–G66). Reads; never writes.

`report(deal, form_key)` → `{form, label, ok, problems, ack}`. `ack` is a short hash of the problem list (code and
text): the download sends it back, and `stale(deal, form_key, ack)` answers the fresh report when it no longer
matches — something changed since the person read the check (G66). No `ack`, no check: a door that never showed the
report (the "Check the form ▸" preview) builds as before.
"""

import hashlib
import json

from documents.review_rules import READ

from .. import forms, values
from ..engine import walk
from ..models import Questionnaire
from ..pdf import build, printed
from ..selectors import context
from . import problems


def digest(found):
    rows = sorted((p['code'], p['text']) for p in found)
    return hashlib.sha256(json.dumps(rows).encode('utf-8')).hexdigest()[:16]


def _open_reads(view):
    """Values Claude read and doubted (or a person flagged) that nobody has looked at: the `to_check` slots on screen
    whose value came from a read."""
    found = values.statuses(view.form, view.stored, view.prefill, view.view)
    return sum(
        1
        for slot, state in found.items()
        if state == 'to_check' and (view.stored.sources.get(slot) or {}).get('origin') == READ
    )


def _waiting(view):
    return sum(1 for entry in view.stored.client.values() if (entry or {}).get('status') == 'pending')


def report(deal, form_key):
    form = forms.FORMS[form_key]
    row = Questionnaire.objects.filter(deal_id=deal.id, form=form_key).first()
    view = context.form_view(form_key, row, context.prefill_facts(deal))
    progress = walk.progress(form, view.view)
    listed = problems.problems(
        form,
        printed.printed(view, row, deal.client.name),
        build.layout_of(form_key),
        started=context.started(row),
        signed=bool(row and row.locked),
        blank=progress['total'] - progress['filled'],
        open_reads=_open_reads(view),
        waiting=_waiting(view),
    )
    return {'form': form_key, 'label': form['title'], 'ok': not listed, 'problems': listed, 'ack': digest(listed)}


def stale(deal, form_key, ack):
    """The fresh report when `ack` no longer matches it, else None."""
    if not ack:
        return None
    fresh = report(deal, form_key)
    return None if fresh['ack'] == ack else fresh
