"""Typed-name signatures and Reopen (plan.md §6.8, §7.9; G49–G55; OQ54, OQ55).

`sign(user, deal_id, form_key, who, name, authorized=False, sign_anyway=False)`:
- the agent signs whenever the agent's signature is missing, before or after the officer (G50);
- staff sign for the company officer only with the officer's written authorization (400 without it), and over
  blank required answers only with "Sign anyway" (409 naming how many; G51). Typed names plus the paper-copy route
  (OQ54 default): a person may also file the officer's paper copy instead;
- a lost deal refuses a signature (409), and a signature already on file is not overwritten (409);
- the officer's signature freezes what the signer saw — every answer on screen still showing the live prefill is
  stored as a `prefill` value — and locks the form (G27, G52). Who signed, on whose authorization and where are kept
  on the row and named in Activity (G53). The signed form is filed as a protected Document (G135; `filing`), and an
  agent's signature after the officer's files a fresh copy (G50).

`reopen(user, deal_id, form_key, reason)` (G54; OQ55 default: any user, with a reason): clears both signatures —
the agent attested to the same answers — keeps `{at, by, reason}` in `reopens`, and drops the frozen prefill nobody
confirmed, so it is live again (G27). The reason stays on the row, never in Activity (free text might name a member's
condition; §3.8). Neither signing nor reopening is reverted through Activity: Reopen is the door.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock, rules
from deals.values import apply, source
from documents.review_rules import is_approved

from .. import forms
from ..engine import walk
from . import common, filing

Signed = namedtuple('Signed', 'row who activity facts')
WHO = ('officer', 'agent')
NAME_LIMIT = 200
AUTHORIZATION = (
    "Signing for the client's officer needs their written authorization: tick the box to confirm you have it."
)
ALREADY = 'This signature is already on file.'
NOT_SIGNED = 'This form is not signed, so there is nothing to reopen.'
REASON_NEEDED = 'Say why the form is reopened.'


class Incomplete(activity.Refused):
    """409 for blank required answers under the officer's signature, with the counts for "Sign anyway"."""

    def __init__(self, filled, total):
        blank = total - filled
        verb = 'answers are' if blank != 1 else 'answer is'
        sentence = f'{blank} required {verb} still blank. Signing as the officer locks the form.'
        super().__init__(sentence)
        self.detail = {'detail': sentence, 'incomplete': {'filled': filled, 'total': total}}


def _name(value):
    text = ' '.join(str(value or '').split())
    if not text:
        raise ValidationError({'name': ['Type the signer’s full name.']})
    if len(text) > NAME_LIMIT:
        raise ValidationError({'name': [f'Keep the name under {NAME_LIMIT} characters.']})
    return text


def _freeze(row, view, user):
    """Store every answer on screen that still shows the live prefill (origin `prefill`): the signer saw it."""
    frozen = {}
    for entry in walk.order(view.form, view.view):
        slot = entry['slot']
        if slot not in row.answers and slot not in row.cleared and view.prefill.get(slot):
            frozen[slot] = view.prefill[slot]
    answers, sources = dict(row.answers), dict(row.sources)
    diff = apply(answers, sources, frozen, source('prefill', user))
    row.answers, row.sources = answers, sources
    return diff


@transaction.atomic
def sign(user, deal_id, form_key, who, name, *, authorized=False, sign_anyway=False, link=None):
    if who not in WHO:
        raise ValidationError({'who': ['Sign as the officer or the agent.']})
    name = _name(name)
    if who == 'officer' and not authorized and link is None:
        raise ValidationError({'authorized': [AUTHORIZATION], 'code': 'authorization_required'})
    deal = common.lock_deal(deal_id)
    refusal = rules.refuses(deal, 'sign')
    if refusal:
        raise activity.Refused(refusal)
    row, _ctx, facts = common.open_row(user, deal, form_key)
    if getattr(row, f'{who}_signed_at') is not None:
        raise activity.Refused(ALREADY)
    now = clock.now()
    by = user if getattr(user, 'is_authenticated', False) else None
    label = forms.label(form_key)
    if who == 'officer':
        view = common.view_of(row, facts)
        found = walk.progress(view.form, view.view)
        if found['filled'] < found['total'] and not sign_anyway:
            raise Incomplete(found['filled'], found['total'])
        _freeze(row, view, user)
        row.officer_name, row.officer_signed_at, row.officer_signed_by = name, now, by
        row.officer_authorized, row.officer_link = bool(authorized), link
        fields = ['answers', 'sources', 'officer_name', 'officer_signed_at', 'officer_signed_by', 'officer_authorized',
                  'officer_link']  # fmt: skip
        where = 'on their link' if link is not None else 'on their written authorization'
        summary = f'{label}: signed for the company officer as {name}, {where}'
    else:
        row.agent_name, row.agent_signed_at, row.agent_signed_by = name, now, by
        fields = ['agent_name', 'agent_signed_at', 'agent_signed_by']
        summary = f'{label}: signed by the agent, {name}'
    filed = None
    if row.locked:  # the officer's signature, or the agent's after it: file what is now signed
        filed = filing.file_copy(user, deal, row, facts, who)
        fields += ['signed_document', 'signed_copies']
        summary += '; the signed copy is filed in Documents'
    common.restamp(row, facts)
    row.save(update_fields=[*fields, 'flags', 'updated_at'])
    record = activity.record(
        deal, user, common.AREA, 'signed', summary, revertible=False, document_id=filed.id if filed else None,
        changes=[activity.change(common.target(row), {f'{who}_signed_at': [None, now.isoformat()]})],
    )  # fmt: skip
    return Signed(row, who, record, facts)


@transaction.atomic
def reopen(user, deal_id, form_key, reason):
    reason = ' '.join(str(reason or '').split())
    if not reason:
        raise ValidationError({'reason': [REASON_NEEDED]})
    if len(reason) > 300:
        raise ValidationError({'reason': ['Keep the reason under 300 characters.']})
    deal = common.lock_deal(deal_id)
    common.form_or_404(form_key)
    row, _ctx, facts = common.open_row(user, deal, form_key, create=False)
    if row is None or not row.locked:
        raise activity.Refused(NOT_SIGNED)
    by = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None
    unconfirmed = {
        slot: ''
        for slot, entry in row.sources.items()
        if (entry or {}).get('origin') == 'prefill' and not is_approved(entry)
    }
    answers, sources = dict(row.answers), dict(row.sources)
    apply(answers, sources, unconfirmed, source('prefill', user))
    row.answers, row.sources = answers, sources
    row.officer_name, row.officer_signed_at, row.officer_signed_by = '', None, None
    row.officer_authorized, row.officer_link = False, None
    row.agent_name, row.agent_signed_at, row.agent_signed_by = '', None, None
    row.signed_document = None
    row.reopens = [*row.reopens, {'at': clock.now().isoformat(), 'by': by, 'reason': reason}]
    common.restamp(row, facts)
    row.save()
    record = activity.record(
        deal, user, common.AREA, 'reopened', f'{forms.label(form_key)}: reopened, the signatures cleared',
        revertible=False,
        changes=[activity.change(common.target(row), {'officer_signed_at': ['signed', None]})],
    )  # fmt: skip
    return Signed(row, 'officer', record, facts)
