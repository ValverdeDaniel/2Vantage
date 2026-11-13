"""A person's decision on the client's questionnaire answers: the questionnaire's side of the owner contract (plan.md
§5.8, §6.8; L.6, O.3.1, O.3.4; G69, G70, G73, G81; OQ84, OQ85; slice 58). Review's queues and section bars call these
through `review.owners`; nothing else moves a client's answer into a form.

A slot here is (form key, slot), the slot as the form stores it (`field` or `block.<row id>.field`).
- `approve_client(user, deal_id, slots)`: each pending answer moves into `Questionnaire.answers` through
  `deals.values.apply()` with its source `{origin: client, by: the approver, link}` (rule 2); a client's answer that
  empties a box showing the live prefill hides the prefill instead (`cleared`, G33). The entry becomes `approved`,
  keeping the value it replaced (`prior` and its source) for `revert_approval`. On a signed form the officer attested
  these answers, so they may still be approved; the approval that takes the last answer waiting files the signed copy
  (OQ85, G135: it prints approved values only).
- `reject_client(user, deal_id, slots)`: "Keep ours" (G70; one writer for Keep ours and Correct's close): nothing but
  the entry changes. A signed form refuses (409): the officer attested their answers, so the form is reopened first.
- `revert_approval(user, deal_id, slots)`: the value the approval replaced comes back and the answer waits again,
  while the answer is still the approved one (409 naming the questions otherwise); a signed form refuses.
Activity (area `questionnaire`): before and after for ordinary answers, keys only for the medical and claimant ones
(G23, rule 4), on their own rows (`common.record_values`), not revertible from Change history (Undo approval is the
way back, as the census's). Lock order: the Deal, then the forms' rows by id (O.3.7).
"""

from collections import namedtuple

from django.db import transaction

from deals import activity, clock
from deals.values import apply as apply_values
from deals.values import source
from intake import client_entries as entries_rule

from .. import forms, slots
from ..engine.spec import field_spec
from ..models import Questionnaire
from ..selectors import context, portal
from . import common, filing

Decided = namedtuple('Decided', 'slots activity')  # slots: [(form, slot)] decided; activity: [Activity rows]

APPROVED, REJECTED, UNAPPROVED = 'approved', 'rejected', 'unapproved'
SIGNED_KEEP = (
    'The company officer signed this form with their answers: reopen it on the Questionnaire tab to keep ours.'
)
SIGNED_BACK = 'This questionnaire is signed: reopen the form before taking an approval back.'
STILL_CHANGED = '{names} changed after the approval, so it cannot be taken back.'
CLEARED = 'cleared:'


def _user_id(user):
    return user.id if getattr(user, 'is_authenticated', False) else None


def label(form_key, slot):
    """'Plan 2 · Current plan name' — what a person reads for one answer, never its value."""
    form = forms.FORMS[form_key]
    found = slots.parse(slot)
    if not found:
        return slot
    block, row_id, key = found
    field = field_spec(form, block, key) or {}
    text = field.get('label') or key
    if not block:
        return text
    spec = form['blocks'][block]
    return f'{spec["row_label"]} · {text}'


def _names(form_key, picked):
    labels = [label(form_key, slot) for slot in picked]
    return labels[0] if len(labels) == 1 else ', '.join(labels[:-1]) + ' and ' + labels[-1]


def _by_form(pairs):
    out = {}
    for form_key, slot in dict.fromkeys(pairs):
        if form_key in forms.FORMS:
            out.setdefault(form_key, []).append(slot)
    return {key: out[key] for key in forms.FORMS if key in out}


def _locked(deal_id, form_keys):
    deal = common.lock_deal(deal_id)
    found = Questionnaire.objects.select_for_update().filter(deal_id=deal_id, form__in=form_keys).order_by('id')
    return deal, {row.form: row for row in found}


def _pending(row, wanted):
    client = (row.client if row else None) or {}
    return [slot for slot in wanted if entries_rule.pending(client.get(slot))]


def _land(user, row, client, wanted, prefill, now):
    """Move the pending answers into the form; returns the diff ({slot: [before, after]}, `cleared:` keys too)."""
    answers, sources, cleared = dict(row.answers), dict(row.sources), list(row.cleared)
    priors = {slot: (answers.get(slot, ''), sources.get(slot)) for slot in wanted}
    changes, diff = {}, {}
    for slot in wanted:
        value = client[slot].get('value', '')
        if value in (None, '') and slot not in answers and prefill.get(slot) and slot not in cleared:
            cleared.append(slot)
            diff[CLEARED + slot] = [False, True]
        else:
            changes[slot] = value
    links = {slot: client[slot].get('link') for slot in wanted}
    diff.update(apply_values(answers, sources, changes, lambda key: source('client', user, link=links[key])))
    for slot in wanted:
        prior, prior_source = priors[slot]
        client[slot] = entries_rule.decided(
            client[slot], entries_rule.APPROVED, _user_id(user), now, prior=prior, prior_source=prior_source
        )
    row.answers, row.sources, row.cleared, row.client = answers, sources, cleared, client
    return diff


def _file_if_done(user, deal, row, facts):
    """A signed form with no copy filed since the signature files one once nothing waits (OQ85, G135)."""
    if not row.locked or row.signed_document_id is not None or portal.waiting(row):
        return None
    return filing.file_copy(user, deal, row, facts, 'officer')


@transaction.atomic
def approve_client(user, deal_id, pairs):
    """Returns Decided([(form, slot) approved], [Activity rows])."""
    grouped = _by_form(pairs)
    deal, rows = _locked(deal_id, list(grouped))
    now = clock.now().isoformat()
    decided, written, facts = [], [], None
    for form_key, wanted in grouped.items():
        row = rows.get(form_key)
        picked = _pending(row, wanted)
        if not picked:
            continue
        facts = facts or context.prefill_facts(deal)
        view = common.view_of(row, facts)
        client = dict(row.client)
        diff = _land(user, row, client, picked, view.prefill, now)
        filed = _file_if_done(user, deal, row, facts)
        common.restamp(row, facts)
        row.save()
        decided += [(form_key, slot) for slot in picked]
        summary = f'approved {_plural(len(picked))}' + ('; the signed copy is filed in Documents' if filed else '')
        if diff:
            plain, hidden = common.record_values(
                deal, user, row, summary, diff, action=APPROVED, coalesce=False, revertible=False
            )
            written += [found for found in (plain, hidden) if found is not None]
        else:
            written.append(_entries_row(deal, user, row, APPROVED, f'{forms.label(form_key)}: {summary}', picked))
    return Decided(decided, written)


def _plural(count):
    return f'{count} client answer{"" if count == 1 else "s"}'


def _entries_row(deal, user, row, action, summary, picked):
    change = activity.change(f'{common.keys_target(row)}:client', sorted(picked))
    return activity.record(deal, user, common.AREA, action, summary, changes=[change], keys_only=True)


@transaction.atomic
def reject_client(user, deal_id, pairs):
    """Keep ours: the pending answers named are rejected and nothing else changes. Returns Decided."""
    grouped = _by_form(pairs)
    deal, rows = _locked(deal_id, list(grouped))
    now = clock.now().isoformat()
    decided, written = [], []
    for form_key, wanted in grouped.items():
        row = rows.get(form_key)
        picked = _pending(row, wanted)
        if not picked:
            continue
        if row.locked:
            raise activity.Refused(SIGNED_KEEP)
        client = dict(row.client)
        for slot in picked:
            client[slot] = entries_rule.decided(client[slot], entries_rule.REJECTED, _user_id(user), now)
        row.client = client
        row.save(update_fields=['client', 'updated_at'])
        decided += [(form_key, slot) for slot in picked]
        summary = f"{forms.label(form_key)}: kept our answer over the client's: {_names(form_key, picked)}"
        written.append(_entries_row(deal, user, row, REJECTED, summary, picked))
    return Decided(decided, written)


@transaction.atomic
def revert_approval(user, deal_id, pairs):
    """Take approvals back: the value each replaced returns and the answer waits again. Returns Decided; 409 on a
    signed form or when an answer changed since it was approved."""
    grouped = _by_form(pairs)
    deal, rows = _locked(deal_id, list(grouped))
    decided, written = [], []
    for form_key, wanted in grouped.items():
        row = rows.get(form_key)
        client = dict((row.client if row else None) or {})
        picked = [slot for slot in wanted if entries_rule.approved(client.get(slot))]
        if not picked:
            continue
        if row.locked:
            raise activity.Refused(SIGNED_BACK)
        moved = [slot for slot in picked if not _still(row, client[slot], slot)]
        if moved:
            raise activity.Refused(STILL_CHANGED.format(names=_names(form_key, moved)), moved)
        answers, sources, cleared = dict(row.answers), dict(row.sources), list(row.cleared)
        diff = {}
        for slot in picked:
            entry = client[slot]
            if slot in cleared and entry.get('value') in (None, '') and slot not in answers:
                cleared.remove(slot)
                diff[CLEARED + slot] = [True, False]
                continue
            back = entry.get('prior', '') or ''
            prior_source = entry.get('prior_source') or source('typed', user)
            diff.update(apply_values(answers, sources, {slot: back}, prior_source))
        for slot in picked:
            client[slot] = entries_rule.decided(client[slot], entries_rule.PENDING, None, None)
        row.answers, row.sources, row.cleared, row.client = answers, sources, cleared, client
        common.restamp(row, context.prefill_facts(deal))
        row.save()
        decided += [(form_key, slot) for slot in picked]
        summary = f"took back the approval of the client's answer: {_names(form_key, picked)}"
        if diff:
            plain, hidden = common.record_values(
                deal, user, row, summary, diff, action=UNAPPROVED, coalesce=False, revertible=False
            )
            written += [found for found in (plain, hidden) if found is not None]
        else:
            written.append(_entries_row(deal, user, row, UNAPPROVED, f'{forms.label(form_key)}: {summary}', picked))
    return Decided(decided, written)


def _still(row, entry, slot):
    """The answer is still the one approved (or, for an emptied prefill, the box is still cleared)."""
    value = entry.get('value', '')
    if value in (None, '') and slot not in row.answers:
        return slot in row.cleared or slot not in row.answers
    return entries_rule.same(row.answers.get(slot, ''), value)
