"""The questionnaires' part of the review queue (plan.md §8.8; L21, G68, G69, G73, G81; old 891f1b3 `items.
questionnaire_review`, `QuestionnaireReview.jsx`): one item per answer the client gave on a form, each form in turn and
its answers in the form's order ("Plan 2 · Current plan name"), what we hold (the stored answer, else the live prefill
the form shows) beside what they sent, the change it makes, and why it is ready. A medical or claimant answer is
flagged `sensitive` (staff only, never a log). On a form the officer signed (`signed`), the answers they attested may
only be approved: Correct and Keep ours wait for a reopen.
"""

from questionnaire import forms, slots, values
from questionnaire.engine import walk
from questionnaire.engine.spec import field_spec
from questionnaire.models import Questionnaire
from questionnaire.selectors import context

from ..rules import items as item_rules
from . import queue_common as common


def label(form, slot, numbers):
    """(label, section label) for one slot: 'Plan 2 · Current plan name', 'Section II. Coverage'."""
    found = slots.parse(slot)
    if not found:
        return slot, ''
    block, row_id, key = found
    field = field_spec(form, block, key) or {}
    text = field.get('label') or key
    for section in form['sections']:
        if (block and block in (section.get('blocks') or [])) or (
            not block and any(f['key'] == key for f in section.get('fields') or [])
        ):
            head = f'Section {section["number"]}. {section["label"]}' if section.get('number') else section['label']
            break
    else:
        head = ''
    if block:
        spec = form['blocks'][block]
        return f'{spec["row_label"]} {numbers.get((block, row_id), "?")} · {text}', head
    return text, head


def _shown(value):
    return '' if value is None else str(value)


def items(deal, entries, links, now):
    by_form = {}
    for entry in entries:
        by_form.setdefault(entry.slot[0], []).append(entry)
    rows = {row.form: row for row in Questionnaire.objects.filter(deal_id=deal.id, form__in=list(by_form))}
    facts = context.prefill_facts(deal) if by_form else None
    out = []
    for form_key in [key for key in forms.FORMS if key in by_form]:
        row = rows.get(form_key)
        if row is None:
            continue
        view = context.form_view(form_key, row, facts)
        bare = values.Stored(view.stored.answers, view.stored.sources, {}, view.stored.cleared, view.stored.rows)
        order = {entry['slot']: at for at, entry in enumerate(walk.order(view.form, view.view))}
        numbers = {
            (block, entry['id']): index + 1
            for block, listed in (row.rows or {}).items()
            for index, entry in enumerate(listed)
        }
        name = forms.label(form_key)
        for entry in sorted(by_form[form_key], key=lambda e: (order.get(e.slot[1], len(order)), e.slot[1])):
            slot = entry.slot[1]
            found = slots.parse(slot) or ('', 0, slot)
            field = field_spec(view.form, found[0], found[2]) or {}
            words, section = label(view.form, slot, numbers)
            ours = values.effective(bare, view.prefill, slot)
            change = item_rules.change(ours, entry.value)
            group_label = f'{name} · {section}' if section else name
            item = common.item(entry, links, now, change=change, group=f'{form_key}:{section}:{change}',
                               group_label=group_label)  # fmt: skip
            item.update(
                kind='answer',
                label=words,
                section=group_label,
                form=form_key,
                ours=_shown(ours),
                theirs=_shown(entry.value),
                required=bool(field.get('required')),
                sensitive=forms.is_sensitive(form_key, found[0], found[2]),
                hidden=slot not in order,
                signed=row.locked,
                editable=not row.locked,
            )
            out.append(item)
    return out
