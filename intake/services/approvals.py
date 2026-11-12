"""A person's decision on the client's intake answers: intake's side of the owner contract (plan.md §5.8, §6.5; L.6,
O.3.1, O.3.4; L17, L43, L85, B38; OQ84, OQ85; slice 55). Review's queues and section bars call these through
`review.owners`; nothing else writes an answer from a client.

- `approve_client(user, deal_id, slots)`: each pending answer among `slots` moves into the values with its source
  `{origin: client, by: the approver, link}` through `deals.values.apply()` (rule 2): a question's answer into
  `Intake.answers` (the target effective date through its door, `deals.services.set_effective_date`), a block through
  its owner's services (`client_blocks`). The entry becomes `approved`, keeping the value it replaced (`prior` and its
  source), so `revert_approval` can put it back. One Activity row per call for the answers, with before and after
  (rule 4; coalescing a run of approvals), which intake's reverter undoes, entries reopened with it; one key-only row
  per approved block, beside the owners' own rows.
- `reject_client(user, deal_id, slots)`: "Keep ours" (L17: one writer for both). Nothing but the entry changes; a
  key-only Activity row says so.
- `revert_approval(user, deal_id, slots)`: an approved answer goes back to the value it replaced and waits again, while
  the answer is still the approved one (409 naming the questions otherwise). Blocks cannot be taken back this way:
  their owners' own rows revert them.
Slots are question keys and `block:contacts|coverage|lines`; a slot with no entry in the needed state is skipped.
Lock order: the Deal, then the Intake row, then (blocks) the client's contacts and the coverage rows by id (O.3.7).
"""

import datetime
from collections import namedtuple

from django.db import transaction

from deals import activity, clock
from deals.services import set_effective_date
from deals.values import apply as apply_values
from deals.values import source

from .. import client_entries as entries_rule
from .. import client_view, flags, form
from ..models import Intake
from . import client_blocks, rows

Decided = namedtuple('Decided', 'slots activity')  # slots: the slots decided; activity: [Activity rows]

APPROVED, REJECTED, UNAPPROVED = 'approved', 'rejected', 'unapproved'
STILL_CHANGED = '{names} changed after the approval, so it cannot be taken back.'
BLOCK_BACK = 'An approved block is taken back from its own changes in Activity.'


def entries_target(deal_id):
    """The target of rows about the entries alone (a block approved, a rejection): never an answer's target, so a
    revert of an earlier answer is not refused because of them."""
    return f'intake.client:{deal_id}'


def _user_id(user):
    return user.id if getattr(user, 'is_authenticated', False) else None


def _label(slot):
    if slot in client_view.BLOCK_SLOTS:
        return {client_view.CONTACTS: 'Contacts', client_view.COVERAGE: 'Current coverage'}.get(slot, 'Lines to quote')
    return form.BY_KEY[slot]['label'] if slot in form.BY_KEY else slot


def _names(slots):
    labels = [_label(slot) for slot in slots]
    return labels[0] if len(labels) == 1 else ', '.join(labels[:-1]) + ' and ' + labels[-1]


def _locked(deal_id):
    deal = rows.lock_deal(deal_id)
    intake = Intake.objects.select_for_update().filter(deal_id=deal_id).first()
    return deal, intake


def _date(value):
    return datetime.date.fromisoformat(value) if value else None


def _write_answers(deal, intake, answers, sources, changed):
    """Store the answers and sources; the effective date through its door. Returns the Activity entries."""
    entries = []
    if form.EFFECTIVE_DATE in changed:
        moved = set_effective_date(deal.id, _date(answers.get(form.EFFECTIVE_DATE)))
        deal.effective_date = _date(answers.get(form.EFFECTIVE_DATE))
        entries.append(activity.change(f'deal:{deal.id}', moved))
    intake.answers = {key: value for key, value in answers.items() if key != form.EFFECTIVE_DATE}
    intake.sources = sources
    flags.stamp(deal, intake)
    kept = {key: pair for key, pair in changed.items() if key != form.EFFECTIVE_DATE}
    if kept:
        entries.insert(0, activity.change(rows.intake_target(deal.id), kept))
    return entries


def _approve_answers(user, deal, intake, client, keys, now):
    from ..selectors import answers_of

    answers = answers_of(deal, intake)
    sources = dict(intake.sources)
    priors = {key: (answers.get(key, ''), sources.get(key)) for key in keys}
    wanted = {key: client[key].get('value', '') for key in keys}
    links = {key: client[key].get('link') for key in keys}
    changed = apply_values(answers, sources, wanted, lambda key: source('client', user, link=links[key]))
    for key in keys:
        prior, prior_source = priors[key]
        client[key] = entries_rule.decided(
            client[key], entries_rule.APPROVED, _user_id(user), now, prior=prior, prior_source=prior_source
        )
    if not changed:
        return None
    entries = _write_answers(deal, intake, answers, sources, changed)
    # "Approved 3 client intake answers": a run of approvals coalesces into one row, which Revert takes back whole.
    return activity.record(
        deal,
        user,
        rows.AREA,
        APPROVED,
        'Approved',
        len(changed),
        'intake:client:approved',
        'client intake answer',
        changes=entries,
    )


def _entries_row(deal, user, action, summary, slots):
    change = activity.change(entries_target(deal.id), sorted(slots))
    return activity.record(deal, user, rows.AREA, action, summary, changes=[change], keys_only=True)


@transaction.atomic
def approve_client(user, deal_id, slots):
    """Returns Decided(the slots approved, [Activity rows])."""
    deal, intake = _locked(deal_id)
    client = dict((intake.client if intake else None) or {})
    wanted = [slot for slot in dict.fromkeys(slots) if entries_rule.pending(client.get(slot))]
    if not wanted:
        return Decided([], [])
    now = clock.now().isoformat()
    written = []
    questions = [slot for slot in wanted if slot in form.KEYS]
    if questions:
        row = _approve_answers(user, deal, intake, client, questions, now)
        written += [row] if row else []
    for slot in [slot for slot in wanted if slot in client_view.BLOCK_SLOTS]:
        landed = client_blocks.land(user, deal, slot, client[slot].get('value'))
        client[slot] = entries_rule.decided(client[slot], entries_rule.APPROVED, _user_id(user), now)
        written.append(_entries_row(deal, user, APPROVED, f"Approved the client's {landed}", [slot]))
    intake.client = client
    intake.save(update_fields=['answers', 'sources', 'flags', 'client', 'updated_at'])
    return Decided(wanted, written)


@transaction.atomic
def reject_client(user, deal_id, slots):
    """Keep ours: the pending answers among `slots` are rejected and nothing else changes. Returns Decided."""
    deal, intake = _locked(deal_id)
    client = dict((intake.client if intake else None) or {})
    wanted = [slot for slot in dict.fromkeys(slots) if entries_rule.pending(client.get(slot))]
    if not wanted:
        return Decided([], [])
    now = clock.now().isoformat()
    for slot in wanted:
        client[slot] = entries_rule.decided(client[slot], entries_rule.REJECTED, _user_id(user), now)
    intake.client = client
    intake.save(update_fields=['client', 'updated_at'])
    summary = f"Kept our value over the client's answer: {_names(wanted)}"
    return Decided(wanted, [_entries_row(deal, user, REJECTED, summary, wanted)])


@transaction.atomic
def revert_approval(user, deal_id, slots):
    """Take an approval back: the value it replaced returns and the answer waits again. Returns Decided; 409 when a
    block is named or an answer changed since it was approved."""
    from ..selectors import answers_of

    deal, intake = _locked(deal_id)
    client = dict((intake.client if intake else None) or {})
    wanted = [slot for slot in dict.fromkeys(slots) if entries_rule.approved(client.get(slot))]
    if any(slot in client_view.BLOCK_SLOTS for slot in wanted):
        raise activity.Refused(BLOCK_BACK)
    if not wanted:
        return Decided([], [])
    answers, sources = answers_of(deal, intake), dict(intake.sources)
    moved = [slot for slot in wanted if not entries_rule.same(answers.get(slot, ''), client[slot].get('value'))]
    if moved:
        raise activity.Refused(STILL_CHANGED.format(names=_names(moved)), moved)
    back = {slot: client[slot].get('prior', '') or '' for slot in wanted}
    priors = {slot: client[slot].get('prior_source') or source('typed', user) for slot in wanted}
    changed = apply_values(answers, sources, back, lambda key: priors[key])
    for slot in wanted:
        client[slot] = entries_rule.decided(client[slot], entries_rule.PENDING, None, None)
    entries = _write_answers(deal, intake, answers, sources, changed) if changed else []
    intake.client = client
    intake.save(update_fields=['answers', 'sources', 'flags', 'client', 'updated_at'])
    summary = f"Took back the approval of the client's answer: {_names(wanted)}"
    row = activity.record(deal, user, rows.AREA, UNAPPROVED, summary, changes=entries, revertible=False)
    return Decided(wanted, [row])


def reopen(intake, keys):
    """Intake's reverter, undoing an approval row: the approved answers among `keys` wait again (in memory)."""
    client = dict(intake.client or {})
    for key in keys:
        if entries_rule.approved(client.get(key)):
            client[key] = entries_rule.decided(client[key], entries_rule.PENDING, None, None)
    intake.client = client
