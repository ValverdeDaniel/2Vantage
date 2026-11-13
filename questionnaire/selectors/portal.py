"""A form as a client's link shows it (plan.md §7.14, §8.20; G83–G98, L91; OQ84, OQ85; slice 58). Reads; never writes.

`link_view(deal, form_key, link_id, picks=None, blank=False, …)` → LinkView(form, whole, row, stored, prefill, view):
- the client sees their answers waiting over what we hold (G51: "on the link, the client's own answers"): a pending
  answer from any link of the deal — on a blank link (L66) only their own — over the stored value, over the live
  prefill (G136 as the client reads it). A staff-typed answer stays under a client's newer one on their page;
- a narrowed ask (`picks`: {fields, blocks}) shows only the picked questions and tables with what they hang on
  (`engine.narrow`, G22): no signature, no paper copy, no carrier PDF.

`state(lv, link_id)` → the payload's part a save answers again: `values` and `bases` (a compare-and-set stamp per slot
on screen, never the value; `intake.client_entries.base`), `rows` ({block: [{id, number, mine}]}; `mine` a row this
link added that holds no approved answer, which the client may remove, G87), `blocks` (the tables shown), `order`,
`blanks`, `options` (each dependent picker's option key, G12), `progress` (G95: over what the client sees),
`broker` (slots on screen the broker fills, read-only on the link: G86) and `colleague` (slots a colleague's answer
shows on, a flag, never a name).
`writable(lv)` is every slot the link may write: each question of the form as asked, in every row it has, but the
broker's and the furniture (row numbers) — the allowlist review's portal checks a save against.
"""

from collections import namedtuple

from intake import client_entries as entries_rule

from .. import forms, slots, values
from ..engine import walk
from ..engine.conditions import block_visible
from ..engine.narrow import narrow
from ..engine.options import option_key
from ..engine.spec import all_field_refs, block_keys
from . import context

LinkView = namedtuple('LinkView', 'form whole row stored prefill view link_id blank')


def visible(entry, link_id, blank):
    return entries_rule.visible(entry, link_id, blank=blank)


def overlaid(stored, link_id, blank):
    """The stored JSON with the client's visible pending answers in place of what we hold."""
    answers = dict(stored.answers)
    for slot, entry in stored.client.items():
        if visible(entry, link_id, blank):
            answers[slot] = entry.get('value', '')
    shown_sources = {slot: src for slot, src in stored.sources.items() if slot in answers}
    return values.Stored(answers, shown_sources, {}, stored.cleared, stored.rows)


def link_view(deal, form_key, link_id, *, picks=None, blank=False, row=None, facts=None, ctx=None):
    whole = forms.FORMS[form_key]
    form = narrow(whole, picks) if picks and (picks.get('fields') or picks.get('blocks')) else whole
    if row is None:
        ctx = ctx or context.deal_context(deal)
        row = ctx.stored.get(form_key)
    facts = facts or context.prefill_facts(deal)
    base = context.form_view(form_key, row, facts)
    stored = overlaid(base.stored, link_id, blank)
    shown = values.shown(form, stored, base.prefill)
    return LinkView(form, whole, row, base.stored, base.prefill, shown, link_id, blank)


def shown_value(lv, slot):
    stored = overlaid(lv.stored, lv.link_id, lv.blank)
    return values.effective(stored, lv.prefill, slot)


def held_value(lv, slot):
    """What we hold for a slot, the client's answers aside: the stored value, else the live prefill."""
    bare = values.Stored(lv.stored.answers, lv.stored.sources, {}, lv.stored.cleared, lv.stored.rows)
    return values.effective(bare, lv.prefill, slot)


def base_of(lv, slot):
    return entries_rule.base(lv.stored.sources.get(slot), lv.stored.client.get(slot), lv.link_id, blank=lv.blank)


def _approved_in(stored, block, row_id):
    prefix = slots.row_prefix(block, row_id)
    return any(slot.startswith(prefix) for slot in stored.answers) or any(
        slot.startswith(prefix) and entries_rule.approved(entry) for slot, entry in stored.client.items()
    )


def mine(lv, block, entry):
    return (
        entry.get('origin') == 'client'
        and entry.get('link') == lv.link_id
        and not _approved_in(lv.stored, block, entry['id'])
    )


def writable(lv):
    """{slot} the link may write: every question of the form as asked, in each row it has; never a broker's field."""
    out = set()
    for block, field in all_field_refs(lv.form):
        if field.get('auto') or field.get('broker'):
            continue
        if not block:
            out.add(field['key'])
            continue
        for row in lv.stored.rows.get(block) or []:
            out.add(slots.key(block, row['id'], field['key']))
    return out


def _broker(form, block, field_key):
    for found_block, field in all_field_refs(form):
        if found_block == block and field['key'] == field_key:
            return bool(field.get('broker'))
    return False


def state(lv):
    form, shown = lv.form, lv.view
    order = walk.order(form, shown)
    on_screen = [entry['slot'] for entry in order]
    scalars, by_block = shown
    options, shown_values, bases, broker, colleague = {}, {}, {}, [], []
    for slot in on_screen:
        block, row_id, field = slots.parse(slot)
        if block:
            row_values = next((v for rid, v in by_block.get(block) or [] if rid == row_id), {})
            found = option_key(form, block, row_values, field)
            if found:
                options[slot] = found
        value = shown_value(lv, slot)
        if value not in (None, ''):
            shown_values[slot] = value
        bases[slot] = base_of(lv, slot)
        if _broker(form, block, field):
            broker.append(slot)
        if entries_rule.by_colleague(lv.stored.client.get(slot), lv.link_id) and not lv.blank:
            colleague.append(slot)
    rows = {
        block: [
            {'id': entry['id'], 'number': index + 1, 'mine': mine(lv, block, entry)}
            for index, entry in enumerate(lv.stored.rows.get(block) or [])
        ]
        for block in block_keys(form)
    }
    return {
        'values': shown_values,
        'bases': bases,
        'rows': rows,
        'blocks': [key for key in block_keys(form) if block_visible(form, key, scalars)],
        'order': on_screen,
        'blanks': walk.blanks(form, shown),
        'options': options,
        'progress': walk.progress(form, shown),
        'broker': broker,
        'colleague': colleague,
    }


def waiting(row):
    """How many client answers wait for a person on this form."""
    return sum(1 for entry in ((row.client if row else None) or {}).values() if entries_rule.pending(entry))
