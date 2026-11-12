"""A Claude read of a filled form: staged, then used or discarded (plan.md §6.8, §10.4, §10.5; D74, D113, G99, G100;
slice 52). The questionnaire reader's `apply` and `discard`; ↶ Undo this run is `read_undo`.

- `stage(user, deal_id, job_id, form, document_id, read)`: what Claude read (cleaned) waits as a `StagedRead`; the
  form is untouched. Activity says counts only: "Claude read a filled Florida Blue 51+: 24 answers, 3 rows".
- `reader_apply(user, deal, job, select=None)`: "Use this scan ▸" / "Apply N selected ▸", in landing.apply's
  transaction (the Deal, then the job, are locked; then the form's row). The entries are worked out again against the
  form as it stands (`reader.review`): `select` None takes the ticked ones, else the refs named ("<form>:<field>",
  "<form>:row:<block>:<n>", or "form:<form>" for every ticked one of a form); a conflict is never written. A signed
  form refuses (409): a read never lands on a signed form (G99). Values land with origin `ai`, their file and page,
  what was read and Claude's doubt; rows the read adds are its own (`origin: ai`, `doc`). One Activity row of
  before/after for ordinary answers, one keys-only row for sensitive ones (rule 4), neither reverted from Change
  history: the read's own Undo puts both back. The staged read is emptied (D74) and keeps what it wrote for that Undo.
- `reader_discard(user, deal, job)`: the read's Discard sets its staged reads aside, emptied.
"""

import copy

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.values import apply, source

from .. import forms, prefill, slots, values
from ..cleaning import clean_batch
from ..models import StagedRead
from ..reader import review
from ..selectors import context
from . import common

NOT_STAGED = 'This read has nothing waiting, so there is nothing to use.'
SIGNED_USE = '{label} is signed, so this read cannot be used. Reopen the form first.'
BAD_SELECT = 'Send the answers to use as a list of their references.'
NOT_TAKEN = '{n} of the chosen answers the form no longer takes were left out.'
CONFLICT = '{n} chosen answers a person stands behind were left as they are.'
UNSURE = 'Claude was not sure of this answer.'
AREAS = ['questionnaire', 'questionnaires', 'activity']


def _plural(count, one, many):
    return f'{count} {one if count == 1 else many}'


def counted(answers, rows):
    parts = [_plural(answers, 'answer', 'answers') if answers else '', _plural(rows, 'row', 'rows') if rows else '']
    return ', '.join(part for part in parts if part) or 'nothing new'


def _by(user):
    return user if getattr(user, 'is_authenticated', False) else None


@transaction.atomic
def stage(user, deal_id, job_id, form_key, document_id, read):
    """The staged read of one form; returns it."""
    deal = common.lock_deal(deal_id)
    staged = StagedRead.objects.create(
        deal=deal, form=form_key, job_id=job_id, document_id=document_id, read=read, created_by=_by(user)
    )
    words = counted(read['counts']['answers'], read['counts']['rows'])
    summary = f'Claude read a filled {forms.label(form_key)}: {words}, waiting for review'
    activity.record(deal, user, common.AREA, 'proposed', summary, document_id=document_id, actor_kind='claude')
    return staged


TICKED = (True, frozenset())  # "Use this scan": every ticked entry, nothing more


def _wanted(select):
    """{form: (every ticked one?, refs named)}, or None for "Use this scan" (the ticked entries of every form)."""
    if select is None:
        return None
    if not isinstance(select, list) or not all(isinstance(ref, str) for ref in select):
        raise ValidationError({'select': [BAD_SELECT]})
    wanted = {}
    for ref in select:
        head, _, rest = ref.partition(':')
        if head == 'form':
            wanted[rest] = (True, wanted.get(rest, (False, set()))[1])
        elif rest:
            wanted.setdefault(head, (False, set()))[1].add(rest)
    return wanted


def _chosen(listed, refs, skipped):
    """The entries to land: the ticked ones and the named ones (`refs`: (every ticked one?, refs named)), never a
    conflict; the answer that opens a section comes with any row of it."""
    ticked, named = refs
    picked = [entry for entry in listed if (ticked and entry['tick']) or entry['ref'] in named]
    conflicts = [entry for entry in picked if entry['state'] == 'conflict']
    if conflicts:
        skipped.append(CONFLICT.format(n=len(conflicts)))
    chosen = [entry for entry in picked if entry['state'] != 'conflict']
    blocks = {entry['block'] for entry in chosen if entry['kind'] == 'row'}
    openers = [entry for entry in listed if entry.get('opens') in blocks and entry not in chosen]
    return openers + chosen


def _batch(user, staged, row, chosen):
    """({slot: value}, {slot: (page, low)}, rows with the read's new ones, {block: [new row ids]}, last row id)."""
    rows, last, added = copy.deepcopy(row.rows or {}), row.last_row_id, {}
    batch, where = {}, {}
    for entry in chosen:
        if entry['kind'] == 'answer':
            batch[entry['slot']] = entry['new']
            where[entry['slot']] = (entry['page'], entry['low'] or None)
            continue
        target, block = entry['target'], entry['block']
        if target is None:
            last += 1
            target = last
            made = {'id': last, 'origin': 'ai', 'doc': staged.document_id, 'by': getattr(user, 'id', None)}
            rows[block] = [*(rows.get(block) or []), {**made, 'at': clock.now().isoformat()}]
            added.setdefault(block, []).append(last)
        for value in entry['values']:
            slot = slots.key(block, target, value['key'])
            batch[slot] = value['new']
            where[slot] = (entry['page'], UNSURE if value['low'] else None)
    return batch, where, rows, added, last


def _use(user, deal, staged, refs, skipped):
    """(Activity rows, questions answered, rows written) for one staged read."""
    peek = context.form_view(
        staged.form, context.deal_context(deal).stored.get(staged.form), context.prefill_facts(deal)
    )
    if peek.row is not None and peek.row.locked:
        raise activity.Refused(SIGNED_USE.format(label=forms.label(staged.form)))
    if not _chosen(review.entries(peek, staged.read, staged.document_id)[0], refs, []):
        return [], 0, 0  # nothing to write: the form's first row is not made for it
    row, _ctx, facts = common.open_row(user, deal, staged.form)
    if row.locked:
        raise activity.Refused(SIGNED_USE.format(label=forms.label(staged.form)))
    chosen = _chosen(review.entries(common.view_of(row, facts), staged.read, staged.document_id)[0], refs, skipped)
    batch, where, rows, added, last = _batch(user, staged, row, chosen)
    form = forms.FORMS[staged.form]
    stored = values.Stored(row.answers or {}, row.sources or {}, row.client or {}, list(row.cleared or []), rows)
    live = prefill.values(form, facts[0], rows)
    cleaned, dropped = clean_batch(form, values.shown(form, stored, live), rows, batch)
    if dropped:
        skipped.append(NOT_TAKEN.format(n=len(dropped)))
    answers, sources = dict(row.answers), dict(row.sources)
    before = {slot: (answers.get(slot), copy.deepcopy(sources.get(slot))) for slot in cleaned}

    def made(slot):
        page, low = where.get(slot, (None, None))
        return source('ai', user, doc=staged.document_id, page=page, low=low, read_value=cleaned[slot])

    diff = apply(answers, sources, {slot: value for slot, value in cleaned.items() if value != ''}, made)
    for block, ids in added.items():
        for row_id in ids:
            diff[f'row:{block}.{row_id}'] = [None, next(r for r in rows[block] if r['id'] == row_id)]
    row.answers, row.sources, row.rows, row.last_row_id = answers, sources, rows, last
    common.restamp(row, facts)
    row.save(update_fields=['answers', 'sources', 'rows', 'last_row_id', 'flags', 'updated_at'])
    answered = sum(1 for key in diff if slots.parse(key) and not slots.parse(key)[0])  # the questions
    new_rows = len({slots.parse(key)[:2] for key in diff if slots.parse(key) and slots.parse(key)[0]})  # rows written
    written = common.record_values(
        deal, user, row, f'used Claude’s read: {counted(answered, new_rows)}', diff,
        action='read', coalesce=False, revertible=False,
    )  # fmt: skip
    staged.landed = {
        'slots': {slot: [*before[slot], answers[slot], sources[slot]] for slot in diff if not slot.startswith('row:')},
        'rows': added,
        'activity_ids': [entry.id for entry in written if entry],
    }
    return [entry for entry in written if entry], answered, new_rows


def reader_apply(user, deal, job, select=None, picks=None):
    """What the landing wrote: {activity_id, activity_ids, areas, summary, skipped, plan_ids, forms}."""
    staged = list(StagedRead.objects.select_for_update().filter(job=job, status=StagedRead.WAITING).order_by('id'))
    if not staged:
        raise activity.Refused(NOT_STAGED)
    wanted = _wanted(select)
    ids, parts, skipped = [], [], []
    for one in staged:
        refs = TICKED if wanted is None else wanted.get(one.form, (False, set()))
        written, answered, new_rows = _use(user, deal, one, refs, skipped)
        ids += [entry.id for entry in written]
        if answered or new_rows:
            parts.append(f'{forms.label(one.form)}: {counted(answered, new_rows)}')
        one.status, one.read, one.resolved_by, one.resolved_at = StagedRead.APPLIED, {}, _by(user), clock.now()
        one.save(update_fields=['status', 'read', 'landed', 'resolved_by', 'resolved_at'])
    return {
        'activity_id': ids[0] if ids else None,
        'activity_ids': ids,
        'areas': AREAS,
        'summary': ' · '.join(parts) or 'nothing new for the questionnaire',
        'skipped': skipped,
        'plan_ids': [],
        'forms': [one.form for one in staged],
    }


def reader_discard(user, deal, job):
    """The read's Discard: its staged reads are set aside, emptied (D74)."""
    for one in StagedRead.objects.select_for_update().filter(job=job, status=StagedRead.WAITING):
        one.status, one.read, one.resolved_by, one.resolved_at = StagedRead.DISCARDED, {}, _by(user), clock.now()
        one.save(update_fields=['status', 'read', 'resolved_by', 'resolved_at'])


def reader_undo(user, deal, job, force=False):
    from .read_undo import undo

    return undo(user, deal, job, force=force)
