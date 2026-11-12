"""The answers with their sources, for the review marks (E103; plan.md §7.9 `…/{form}/sources/`).

One row per answer on screen that holds a value: its ref (`questionnaire:<form>:<slot>`), label, the value, where it
came from (origin, file and page, doubt), its mark and approval, and whether it is an open warning. A live prefill
row says so (`prefill`): approving it stores it (G27). Questionnaire answers are never located (E103).
"""

from documents.review_rules import is_dealt, mark_state, open_warning

from .. import slots, values
from ..engine import walk
from ..engine.spec import field_spec, get_block
from . import context


def ref(form_key, slot):
    return f'questionnaire:{form_key}:{slot}'


def label_of(form, slot):
    block, row_id, field_key = slots.parse(slot)
    field = field_spec(form, block, field_key) or {}
    if not block:
        return field.get('label', field_key)
    return f'{get_block(form, block)["row_label"]} · {field.get("label", field_key)}'


def source_rows(deal, form_key):
    ctx = context.deal_context(deal)
    view = context.form_view(form_key, ctx.stored.get(form_key), context.prefill_facts(deal))
    rows = []
    counts = {'open': 0, 'check': 0}
    for entry in walk.order(view.form, view.view):
        slot = entry['slot']
        value, where = values.layer(view.stored, view.prefill, slot)
        if value in (None, ''):
            continue
        source = view.stored.sources.get(slot) if where in ('typed', 'stored') else None
        is_open = open_warning(source)
        counts['open'] += bool(is_open)
        counts['check'] += mark_state(source) == 'check'
        rows.append(
            {
                'ref': ref(form_key, slot),
                'slot': slot,
                'label': label_of(view.form, slot),
                'value': value,
                'where': where,
                'origin': (source or {}).get('origin', 'prefill' if where == 'prefill' else ''),
                'doc': (source or {}).get('doc'),
                'page': (source or {}).get('page'),
                'low': bool((source or {}).get('low')),
                'mark': mark_state(source),
                'confirmed': (source or {}).get('confirmed'),
                'open': is_open,
                'dealt': is_dealt(source),
            }
        )
    return {'rows': rows, 'counts': counts}
