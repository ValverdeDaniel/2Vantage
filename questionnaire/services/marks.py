"""Reviewing questionnaire answers: approve, ignore, needs checking and clear (E103; plan.md §7.9, §10.7; E85–E88).

`mark_answers(user, deal_id, form_key, action, refs=None)` is `POST …/{form}/marks/`, the same rule as the Advisor's
and intake's marks (`documents.review_rules.apply_mark`). It names its answers one of two ways (E86):
- `refs`: exactly those answers (`questionnaire:<form>:<slot>`), whatever their state — a blank takes no mark;
- none: the open warnings on screen (for `clear`, the marked ones), so the bar never touches more than it counts.
A mark on an answer still showing the live prefill stores it first (origin `prefill`): confirming prefill freezes it
(G27). A client's waiting answer is reviewed through Review (slice 53), never here. A signed form refuses (409).
One Activity row (`marked`, never merged) holds each answer's marks before and after under `mark.<slot>` — marks,
never values — plus the value a confirmation froze. Marks are bookkeeping: `updated_at` stays unless a value froze.
Revert (E88) puts back the marks still as the row left them, and lets a frozen prefill go live again.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.values import apply, source
from documents.review_rules import ACTIONS, CLEAR, apply_mark, mark_state, marks_of, open_warning, with_marks

from .. import forms, slots, values
from ..engine import walk
from . import common

Marked = namedtuple('Marked', 'action slots row activity facts')
PREFIX = 'mark.'
DONE = {'approve': 'Approved', 'ignore': 'Ignored', 'check': 'Flagged', 'clear': 'Unmarked'}
NOT_HERE = 'Some of those are not answers on this form.'


def parse_refs(form_key, raw):
    """["questionnaire:<form>:<slot>", ...] → [slots]; 400 for an empty list or a ref that is not this form's."""
    if not isinstance(raw, list) or not raw:
        raise ValidationError({'refs': ['Name the answers to review.']})
    out = []
    for ref in raw:
        kind, _, rest = str(ref).partition(':')
        form, _, slot = rest.partition(':')
        if kind != 'questionnaire' or form != form_key or slots.parse(slot) is None:
            raise ValidationError({'refs': [NOT_HERE]})
        out.append(slot)
    return list(dict.fromkeys(out))


def _scoped(view, action):
    wanted = mark_state if action == CLEAR else open_warning
    return [e['slot'] for e in walk.order(view.form, view.view) if wanted(view.stored.sources.get(e['slot']))]


@transaction.atomic
def mark_answers(user, deal_id, form_key, action, *, refs=None):
    if action not in ACTIONS:
        raise ValidationError({'action': ['The action is approve, ignore, check or clear.']})
    common.form_or_404(form_key)
    picked = parse_refs(form_key, refs) if refs is not None else None
    deal = common.lock_deal(deal_id)
    row, _ctx, facts = common.open_row(user, deal, form_key, create=picked is not None)
    if row is None:
        return Marked(action, [], None, None, facts)
    common.refuse_locked(row)
    view = common.view_of(row, facts)
    on_screen = {e['slot'] for e in walk.order(view.form, view.view)}
    picked = [s for s in picked if s in on_screen] if picked is not None else _scoped(view, action)
    by = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None
    at = clock.now().isoformat()
    answers, sources, diff = dict(row.answers), dict(row.sources), {}
    for slot in picked:
        value, where = values.layer(view.stored, view.prefill, slot)
        if value in (None, '') or where == 'client':
            continue
        if where == 'prefill':
            if action == CLEAR:
                continue
            diff.update(apply(answers, sources, {slot: value}, source('prefill', user)))
        entry = sources.get(slot)
        after = apply_mark(entry, action, by, at)
        if after is None:
            continue
        sources[slot] = after
        diff[PREFIX + slot] = [marks_of(entry) if where != 'prefill' else None, marks_of(after)]
    if not diff:
        return Marked(action, [], row, None, facts)
    froze = any(not key.startswith(PREFIX) for key in diff)
    row.answers, row.sources = answers, sources
    common.restamp(row, facts)
    row.save(update_fields=['answers', 'sources', 'flags', *(['updated_at'] if froze else [])])
    marked = [key.removeprefix(PREFIX) for key in diff if key.startswith(PREFIX)]
    what = 'answer' if len(marked) == 1 else 'answers'
    tail = ' as needing checking' if action == 'check' else ''
    summary = f'{forms.label(form_key)}: {DONE[action].lower()} {len(marked)} {what}{tail}'
    record = activity.record(
        deal, user, common.AREA, 'marked', summary,
        count=len(marked), changes=[activity.change(common.target(row), diff)],
    )  # fmt: skip
    return Marked(action, marked, row, record, facts)


def revert(row_activity, user, row):
    """Put back the marks of one `marked` row on the answers still as it left them; a value it froze goes back to
    live prefill. Refuses, naming them, when none is."""
    diff = next((e['k'] for e in row_activity.changes if isinstance(e['k'], dict)), {})
    answers, sources = dict(row.answers), dict(row.sources)
    written, missed = {}, []
    for name, (before, after) in diff.items():
        if not name.startswith(PREFIX):
            continue
        slot = name.removeprefix(PREFIX)
        current = sources.get(slot)
        if current is None or marks_of(current) != after:
            missed.append(slot)
            continue
        if slot in diff and diff[slot][0] is None:  # the mark froze a live prefill: let it go live again
            written.update(apply(answers, sources, {slot: ''}, source('prefill', user)))
        else:
            sources[slot] = with_marks(current, before)
        written[name] = [after, before]
    if not written:
        from .answers import label_of

        raise activity.changed_since([label_of(forms.FORMS[row.form], s) for s in missed], missed)
    row.answers, row.sources = answers, sources
    return row, written
