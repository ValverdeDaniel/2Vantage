"""The questionnaires' part of review's marks across owners (plan.md §10.7, §8.6; M88–M91; M.6 `mark_document`;
slice 64).

`mark(user, deal, action, document_id=…|refs=…, at=…)` marks stored answers the way `marks.mark_answers` does — the
one rule, `documents.review_rules.apply_mark`, then each form's `flags` restamped — but records no Activity of its
own: review writes the one row for every owner (marks only, never an answer: §3.8), and its Revert hands each form's
entries back to the questionnaire's own (`marks.revert`, through `reverters['questionnaire']`). It names its answers
one of two ways:
- `document_id`: the stored answers read from that file that the action takes (`review_rules.takes`), on every form
  not signed (a signed form takes no mark; its answers are frozen with the signature, G52);
- `refs`: exactly those answers (`questionnaire:<form>:<slot>`), whatever their state; 400 for one not stored on this
  deal's form, 409 on a signed form.
A live prefill is not stored and is not touched here (confirming it is the form's own door, G27). The caller has
locked the Deal; this locks the forms by id (O.3.7). Marks are bookkeeping: `updated_at` stays.
"""

from rest_framework.exceptions import ValidationError

from deals import activity
from documents.review_rules import apply_mark, marks_of, takes

from ..models import Questionnaire
from ..selectors import context
from . import common
from .marks import NOT_HERE, PREFIX, parse_refs


def _wanted(refs):
    """{form: [slots]} from refs; 400 for a ref that is not a questionnaire answer's."""
    by_form = {}
    for ref in refs if isinstance(refs, list) else []:
        kind, _, rest = str(ref).partition(':')
        form, _, _slot = rest.partition(':')
        if kind != 'questionnaire' or not form:
            raise ValidationError({'refs': [NOT_HERE]})
        by_form.setdefault(form, []).append(ref)
    if not by_form:
        raise ValidationError({'refs': ['Name the answers to review.']})
    return {form: parse_refs(form, named) for form, named in by_form.items()}


def mark(user, deal, action, *, document_id=None, refs=None, at):
    wanted = _wanted(refs) if refs is not None else None
    found = Questionnaire.objects.select_for_update().filter(deal_id=deal.id)
    if wanted is not None:
        found = found.filter(form__in=sorted(wanted))
    rows = list(found.order_by('id'))
    if wanted is not None and len(rows) != len(wanted):
        raise ValidationError({'refs': [NOT_HERE]})
    by = user.id if getattr(user, 'is_authenticated', False) else None
    facts, changes = None, []
    for row in rows:
        if wanted is not None:
            common.refuse_locked(row)
            slots = wanted[row.form]
        elif row.locked:
            continue
        else:
            slots = [s for s, e in row.sources.items() if (e or {}).get('doc') == document_id and takes(action, e)]
        sources, diff = dict(row.sources), {}
        for slot in slots:
            if row.answers.get(slot) in (None, ''):
                continue  # a blank (or a live prefill, never stored) takes no mark here
            entry = sources.get(slot)
            after = apply_mark(entry, action, by, at)
            if after is None:
                continue
            sources[slot] = after
            diff[PREFIX + slot] = [marks_of(entry), marks_of(after)]
        if not diff:
            continue
        facts = facts or context.prefill_facts(deal)
        row.sources = sources
        common.restamp(row, facts)
        row.save(update_fields=['sources', 'flags'])  # bookkeeping: `updated_at` stays
        changes.append(activity.change(common.target(row), diff))
    return changes
