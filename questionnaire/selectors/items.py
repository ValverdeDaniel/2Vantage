"""`intake.providers.questionnaire_items` (plan.md §5.2; B22, B26; G11): the checklist's two form rows.

{item: {form, source, needed, armed, started, progress, signed, done}} — the form the item uses (or '' for upload
only and not needed), who set it, whether the item asks for anything, and the form's state. `done` is the officer's
signature: a client upload counts through the checklist's own document rule once accepted (G11's fix waits for the
portal, slice 54). Progress is read only for an armed form that is started, so a deal nobody wrote reads no prefill.
"""

from deals import batch
from deals.models import Deal

from . import context
from .payload import progress_of


def questionnaire_items(deal_id):
    if batch.holds(deal_id):
        deal = batch.deal(deal_id)
    else:
        deal = Deal.objects.filter(pk=deal_id).select_related('client').first()
    if deal is None:
        return {}
    ctx = context.deal_context(deal)
    facts_and_order = None
    out = {}
    for item, resolved in ctx.resolved.items():
        key = resolved['form']
        row = ctx.stored.get(key) if key else None
        signed = bool(row and row.officer_signed_at)
        progress = None
        if key and context.started(row):
            facts_and_order = facts_and_order or context.prefill_facts(deal)
            progress = progress_of(key, row, facts_and_order)
        out[item] = {
            'form': key,
            'source': resolved['source'],
            'needed': resolved['needed'],
            'armed': bool(key),
            'started': context.started(row),
            'progress': progress,
            'signed': signed,
            'done': signed,
            'notice': resolved['notice'],
        }
    return out
