"""What the questionnaire services share (plan.md §3.7, §6.8; G.6 rules, O.3.7).

Lock order: the Deal, then intake's row (a choice, or the band frozen by a first write), then the Questionnaire row.
`open_row` gets or creates the row on the first write — with its starting rows (one per current medical plan, then
blanks up to each block's minimum, ids 1..n in the order the payload showed them), after freezing the band's form
into the checklist choice (G133) — and locks it. A form the deal neither arms nor has started is refused.
`record_values` writes the Activity of a values change: before and after per slot for ordinary answers, keys only for
sensitive ones (G23; never a medical answer in Activity), each on its own row. `restamp` rewrites the stored flags.
"""

from django.db import IntegrityError, transaction

from deals import activity
from deals.models import Deal
from deals.values import locked

from .. import forms, prefill, values
from ..models import Questionnaire
from ..selectors import context

AREA = 'questionnaire'
LOCKED = 'This questionnaire is signed and can no longer be edited. Reopen the form to change it.'
NOT_USED = 'This deal does not use that form. Choose it on the marketing checklist first.'
UNKNOWN_FORM = 'Unknown questionnaire form.'


def target(row):
    return f'questionnaire:{row.id}'


def keys_target(row):
    return f'questionnaire:{row.id}:keys'


def lock_deal(deal_id):
    return locked(Deal, deal_id)


def form_or_404(form_key):
    from django.http import Http404

    if form_key not in forms.FORMS:
        raise Http404(UNKNOWN_FORM)
    return forms.FORMS[form_key]


def _freeze_band(user, deal, ctx, form_key):
    """The first write freezes the band's form into the checklist choice (source `band`; G133)."""
    from intake.services import set_form_choice

    form = forms.FORMS[form_key]
    item = forms.item_of(form)
    resolved = ctx.resolved[item]
    if resolved['form'] == form_key and resolved['choice'] == forms.AUTO:
        set_form_choice(
            user, deal.id, item, form_key, 'band', summary=f'Chose {forms.label(form_key)} by group size (first answer)'
        )


def open_row(user, deal, form_key, *, create=True):
    """(row locked, ctx, facts) for a write; the Deal is already locked. Creates the row on the first write."""
    form_or_404(form_key)
    ctx = context.deal_context(deal)
    row = ctx.stored.get(form_key)
    if row is None and not context.armed(ctx, form_key):
        raise activity.Refused(NOT_USED)
    facts_and_order = context.prefill_facts(deal)
    if row is None:
        if not create:
            return None, ctx, facts_and_order
        _freeze_band(user, deal, ctx, form_key)
        starting, last = prefill.starting_rows(forms.FORMS[form_key], facts_and_order[1])
        try:
            with transaction.atomic():
                Questionnaire.objects.create(
                    deal=deal, form=form_key, form_version=forms.FORMS[form_key]['version'], rows=starting,
                    last_row_id=last,
                )  # fmt: skip
        except IntegrityError:
            pass  # another first write made it: lock and use that one
        ctx = context.deal_context(deal)
    row = Questionnaire.objects.select_for_update().get(deal_id=deal.id, form=form_key)
    return row, ctx, facts_and_order


def refuse_locked(row):
    if row is not None and row.locked:
        raise activity.Refused(LOCKED)


def view_of(row, facts_and_order):
    return context.form_view(row.form, row, facts_and_order)


def restamp(row, facts_and_order):
    """Rewrite the stored count of open warnings (O.3.7) on the instance; the caller saves it."""
    view = view_of(row, facts_and_order)
    row.flags = values.flags(view.form, view.stored, view.prefill)


def split_diff(form_key, diff):
    """({slot: [before, after]} of ordinary slots, [sensitive slots]) — a medical answer's value never reaches
    Activity (G23, §3.8)."""
    from .. import slots

    plain, hidden = {}, []
    for key, pair in diff.items():
        slot = key.split(':', 1)[1] if key.startswith('cleared:') else key
        found = slots.parse(slot)
        if found and forms.is_sensitive(form_key, found[0], found[2]):
            hidden.append(key)
        else:
            plain[key] = pair
    return plain, hidden


def record_values(deal, user, row, summary, diff, *, action='answers', coalesce=True, noun='answer'):
    """Activity for a change of values: (plain row or None, keys-only row or None). Bursts coalesce per form."""
    plain, hidden = split_diff(row.form, diff)
    label = forms.label(row.form)
    written = [None, None]
    if plain:
        written[0] = activity.record(
            deal, user, AREA, action, f'{label}: {summary}', count=len(plain),
            coalesce_key=target(row) if coalesce else '', noun=noun,
            changes=[activity.change(target(row), plain)],
        )  # fmt: skip
    if hidden:
        written[1] = activity.record(
            deal, user, AREA, action, f'{label}: {summary}', count=len(hidden),
            coalesce_key=keys_target(row) if coalesce else '', noun=f'medical {noun}',
            changes=[activity.change(keys_target(row), hidden)], keys_only=True,
        )  # fmt: skip
    return tuple(written)
