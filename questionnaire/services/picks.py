"""The form choice (plan.md §7.9; G2, G4, G9, G133).

`choose_form(user, deal_id, item, choice)` is `PATCH deals/{id}/questionnaires/choice/`: the checklist row's picker,
the band notice's Keep and Switch, and (later) the coverage panel and the Overview card all write it. It checks the
choice against the catalogue (`questionnaire/forms`), refuses (409) a swap away from a signed form — the band cannot
swap it either, since the first write froze the choice (G133) — then stores it through intake's `set_form_choice`
with source `producer`. Keep is choosing the kept form: the band's freeze becomes a person's choice and the notice
goes. Locks: the Deal, then intake's row (inside `set_form_choice`). The signed check reads the form without its own
lock: every questionnaire write, signing included, takes the Deal's lock first, so none can sign meanwhile.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity

from .. import forms
from ..models import Questionnaire
from ..selectors import context
from . import common

NOT_AN_ITEM = 'Pick the medical questionnaire or the stop-loss disclosure.'
NOT_A_CHOICE = 'That is not a form this item can use.'


def _clean(item, choice):
    if item not in forms.ITEMS:
        raise ValidationError({'item': [NOT_AN_ITEM]})
    choice = forms.normal_choice(item, choice)
    if choice not in forms.choices(item):
        raise ValidationError({'choice': [NOT_A_CHOICE]})
    return choice


def _summary(item, choice):
    if choice in forms.FORMS:
        return f'Chose {forms.label(choice)} for the {_item_words(item)}'
    if choice == forms.AUTO:
        return f'Set the {_item_words(item)} to follow the group size'
    if choice == forms.UPLOAD:
        return f'Set the {_item_words(item)} to upload only'
    return f'Marked the {_item_words(item)} not needed'


def _item_words(item):
    return 'medical questionnaire' if forms.ITEMS[item] == forms.MEDICAL else 'stop-loss disclosure'


@transaction.atomic
def choose_form(user, deal_id, item, choice):
    """Ticked(item, entry, activity) from intake, or None when nothing changed."""
    from intake.services import set_form_choice

    choice = _clean(item, choice)
    deal = common.lock_deal(deal_id)
    ctx = context.deal_context(deal)
    resolved = ctx.resolved[item]
    current = resolved['form'] or (resolved['choice'] if resolved['choice'] in forms.FORMS else '')
    becomes = resolved['band_form'] if choice == forms.AUTO else (choice if choice in forms.FORMS else '')
    if current and current != becomes:
        signed = Questionnaire.objects.filter(deal_id=deal.id, form=current).first()
        if signed is not None and signed.locked:
            raise activity.Refused(forms.SIGNED_LOCK)
    stored = '' if choice in (forms.AUTO, forms.NOT_NEEDED) else choice
    return set_form_choice(user, deal.id, item, stored, 'producer', summary=_summary(item, choice))
