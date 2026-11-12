"""↶ Undo this run for a questionnaire read (plan.md §10.5; D73, G99; slice 52): the reader's `undo`.

In landing.undo's transaction (the Deal, then the job, are locked), each form the read wrote goes back exactly: every
answer to its value and source before the read (a slot that showed the live prefill shows it again), and the rows the
read added come off unless someone wrote into them since (they stay, counted). What it puts back comes from the staged
read's `landed`, never from Activity, which holds a sensitive answer's key only (rule 4). An answer changed since the
read refuses the whole Undo with the keys (409 with `can_force`); `force` ("Undo anyway") leaves those as they are and
puts back the rest. A signed form refuses: reopen it first. The Undo records Activity as the landing did — before and
after for ordinary answers, keys only for sensitive ones.
"""

from deals import activity, clock

from .. import forms, slots
from ..models import Questionnaire, StagedRead
from ..selectors import context
from . import common
from .reads import counted

SIGNED_UNDO = '{label} is signed, so Claude’s read cannot be undone. Reopen the form first.'
CHANGED = '{n} of the answers this read wrote changed after it, so it cannot be undone as a whole.'
LEFT = '{n} answers changed since were left as they are.'
KEPT = '{rows} the read added'


def _same_source(now, then):
    """The read's own entry still stands (the locator's answer aside)."""
    if not isinstance(now, dict) or not isinstance(then, dict):
        return False
    return {k: v for k, v in now.items() if k != 'loc'} == {k: v for k, v in then.items() if k != 'loc'}


def _put_back(row, landed, force, skipped):
    """The diff of putting one form back, applied to the row in place."""
    answers, sources = dict(row.answers), dict(row.sources)
    written = landed.get('slots') or {}
    moved = [
        slot for slot, (_b, _bs, after, after_source) in written.items()
        if answers.get(slot) != after or not _same_source(sources.get(slot), after_source)
    ]  # fmt: skip
    if moved and not force:
        raise activity.Refused(CHANGED.format(n=len(moved)), sorted(moved))
    if moved:
        skipped.append(LEFT.format(n=len(moved)))
    diff = {}
    for slot, (before, before_source, after, _after_source) in written.items():
        if slot in moved:
            continue
        if before is None:
            answers.pop(slot, None)
            sources.pop(slot, None)
        else:
            answers[slot] = before
            if before_source:
                sources[slot] = before_source
        diff[slot] = [after, before]
    rows, kept = dict(row.rows or {}), 0
    for block, ids in (landed.get('rows') or {}).items():
        for row_id in ids:
            prefix = slots.row_prefix(block, row_id)
            if any(slot.startswith(prefix) for slot in [*answers, *(row.client or {})]):
                kept += 1
                continue
            entry = next((r for r in rows.get(block) or [] if r['id'] == row_id), None)
            if entry is not None:
                rows[block] = [r for r in rows[block] if r['id'] != row_id]
                diff[f'row:{block}.{row_id}'] = [entry, None]
    row.answers, row.sources, row.rows = answers, sources, rows
    return diff, kept


def undo(user, deal, job, force=False):
    """{reverted: [Activity ids], kept: [words], skipped: [sentences], at, by}."""
    reverted, kept, skipped = [], [], []
    for staged in StagedRead.objects.select_for_update().filter(job=job, status=StagedRead.APPLIED).order_by('id'):
        row = Questionnaire.objects.select_for_update().filter(deal_id=deal.id, form=staged.form).first()
        if row is not None and row.locked:
            raise activity.Refused(SIGNED_UNDO.format(label=forms.label(staged.form)))
        if row is not None and staged.landed:
            diff, rows_kept = _put_back(row, staged.landed, force, skipped)
            common.restamp(row, context.prefill_facts(deal))
            row.save(update_fields=['answers', 'sources', 'rows', 'flags', 'updated_at'])
            if rows_kept:
                kept.append(KEPT.format(rows='1 row' if rows_kept == 1 else f'{rows_kept} rows'))
            answered = sum(1 for key in diff if slots.parse(key) and not slots.parse(key)[0])
            removed = sum(1 for key in diff if key.startswith('row:'))
            written = common.record_values(
                deal, user, row, f'undid Claude’s read: {counted(answered, removed)}', diff,
                action='read', coalesce=False, revertible=False,
            ) if diff else (None, None)  # fmt: skip
            reverted += [entry.id for entry in written if entry]
        staged.status, staged.landed = StagedRead.UNDONE, {}
        staged.save(update_fields=['status', 'landed'])
    return {'reverted': reverted, 'kept': kept, 'skipped': skipped, 'at': clock.now().isoformat(), 'by': user.id}
