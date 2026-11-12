"""What a form shows for its answers, in order (G19, G20, G25, G41). Pure.

The engine reads a `shown` view of one questionnaire: `(scalars, rows)` where `scalars` is {field: value} and `rows`
is {block: [(row id, {field: value})]} in row order — each the effective value (`questionnaire/values.py`). From it:
- `visible_fields`: a field is hidden by an effect its row's choices do not turn on, an unmet `visible_if`, or (a
  dependent picker) an empty option list;
- `order`: every slot on screen, in the Form's order (a section's fields, its blocks' rows, then the fields placed
  after the blocks), each with its required flag — what Enter and Tab walk (G41);
- `progress` and `blanks`: one walk over the visible required slots, so the count and the list never disagree (G20);
- `visible_values`: the answers with everything hidden dropped, what every export prints (G19).
"""

from .. import slots
from .conditions import block_visible, condition_met
from .options import active_effects, resolve_options
from .spec import fields_for, get_block


def visible_fields(form, block_key, values):
    """The field keys shown for one row (or for the scalars)."""
    effects = active_effects(form, block_key, values) if block_key else {}
    shown = set()
    for field in fields_for(form, block_key):
        effect = field.get('effect')
        if effect and not effects.get(effect):
            continue
        if not condition_met(field.get('visible_if'), values):
            continue
        if field.get('depends_on') and not resolve_options(form, block_key, values, field['key']):
            continue
        shown.add(field['key'])
    return shown


def _entry(block, row_id, field):
    return {'slot': slots.key(block, row_id, field['key']), 'required': bool(field.get('required'))}


def order(form, shown):
    """[{slot, required}] for every answer on screen, in the Form's order. Auto fields (row numbers) are furniture,
    never answers."""
    scalars, rows = shown
    visible = visible_fields(form, '', scalars)
    out = []
    for section in form['sections']:
        fields = [f for f in section.get('fields') or [] if f['key'] in visible and not f.get('auto')]
        out.extend(_entry('', 0, f) for f in fields if f.get('placement') != 'after_blocks')
        for block_key in section.get('blocks') or []:
            if not block_visible(form, block_key, scalars):
                continue
            for row_id, values in rows.get(block_key) or []:
                row_visible = visible_fields(form, block_key, values)
                out.extend(
                    _entry(block_key, row_id, f)
                    for f in fields_for(form, block_key)
                    if f['key'] in row_visible and not f.get('auto')
                )
        out.extend(_entry('', 0, f) for f in fields if f.get('placement') == 'after_blocks')
    return out


def _blank(value):
    return value is None or not str(value).strip()


def _value_of(shown, slot):
    scalars, rows = shown
    block, row_id, field = slots.parse(slot)
    if not block:
        return scalars.get(field)
    for found_id, values in rows.get(block) or []:
        if found_id == row_id:
            return values.get(field)
    return None


def blanks(form, shown):
    """The required answers on screen still blank, as slot keys, in the Form's order."""
    return [
        entry['slot'] for entry in order(form, shown) if entry['required'] and _blank(_value_of(shown, entry['slot']))
    ]


def progress(form, shown):
    """{filled, total, pct} over the required answers on screen: a Diabetes row does not count the surgery boxes it
    never shows. A form with no required answer on screen is 100% complete."""
    required = [entry['slot'] for entry in order(form, shown) if entry['required']]
    filled = sum(1 for slot in required if not _blank(_value_of(shown, slot)))
    total = len(required)
    return {'filled': filled, 'total': total, 'pct': round(filled / total * 100) if total else 100}


def visible_values(form, shown):
    """The view with every hidden answer dropped (a carrier name after Q13's "No", surgery counts left from another
    category): nothing is deleted, flipping the gate back restores them; exports print only these."""
    scalars, rows = shown
    visible = visible_fields(form, '', scalars)
    out_rows = {}
    for block_key, block_rows in rows.items():
        if not get_block(form, block_key) or not block_visible(form, block_key, scalars):
            out_rows[block_key] = []
            continue
        out_rows[block_key] = [
            (row_id, {k: v for k, v in values.items() if k in visible_fields(form, block_key, values)})
            for row_id, values in block_rows
        ]
    return {k: v for k, v in scalars.items() if k in visible}, out_rows
