"""The stop-loss disclosure's state for quotes' Binding Notes (G117, O.6 #47): fills `quotes.providers.
disclosure_state`. Signed once the officer has signed; started once it holds an answer, a client's entry or a
signature (`context.started`); else not started. Reads one row per stop-loss form; never writes."""

from quotes import providers

from .. import forms
from ..models import Questionnaire
from .context import started

STOP_LOSS_FORMS = [key for key, form in forms.FORMS.items() if form['kind'] == forms.STOP_LOSS_KIND]


def disclosure_state(deal_id):
    rows = list(Questionnaire.objects.filter(deal_id=deal_id, form__in=STOP_LOSS_FORMS))
    if any(row.locked for row in rows):
        return providers.SIGNED
    if any(started(row) for row in rows):
        return providers.STARTED
    return providers.NOT_STARTED
