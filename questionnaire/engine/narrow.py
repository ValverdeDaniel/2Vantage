"""A form as a link asks it, and the questions others hang on (G22, G24, G25). Pure.

- `drivers(form)`: {(block, field)} of every question whose answer changes what else is on the form — another
  question's showing or choices, a block's gate, a row's effects, or a picker's `pair_with` twin. The spec payload
  marks them `driver`, and Enter or Tab on one waits for the save's reply, so a question it reveals is next (G25).
- `narrow(form, pick)`: only the picked questions (`fields`) and tables (`blocks`), with what each depends on and
  what shows on it; a table comes whole with its gate. A narrowed form has no signature, upload or carrier PDF: it is
  answered on a link and signed nowhere (G22, D-187). The portal reads it (slice 54).
"""

from .spec import all_field_refs, block_keys, get_block, section_fields


def _parents(field):
    cond = field.get('visible_if') or {}
    return [key for key in (cond.get('field'), field.get('depends_on')) if key]


def drivers(form):
    out = set()
    for block_key, field in all_field_refs(form):
        out.update((block_key, key) for key in _parents(field))
        if field.get('pair_with'):
            out.add((block_key, field['key']))
    for block_key in block_keys(form):
        block = get_block(form, block_key)
        gate = (block.get('visible_if') or {}).get('field')
        if gate:
            out.add(('', gate))
        for field_key in (block.get('effect_drivers') or {}).values():
            out.add((block_key, field_key))
    return out


def narrow(form, pick):
    """The form as `pick` ({fields, blocks}) asks it, or the form itself when `pick` is None."""
    if pick is None:
        return form
    scalars = {f['key']: f for f in section_fields(form)}
    fields = {key for key in pick.get('fields') or () if key in scalars}
    blocks = {key for key in pick.get('blocks') or () if get_block(form, key)}
    for key in blocks:
        gate = (get_block(form, key).get('visible_if') or {}).get('field')
        if gate in scalars:
            fields.add(gate)
    moved = True
    while moved:
        moved = False
        for key, field in scalars.items():
            parents = [p for p in _parents(field) if p in scalars]
            partner = field.get('pair_with')
            if key in fields:
                wanted = [*parents, *([partner] if partner in scalars else [])]
            elif any(p in fields for p in parents) or partner in fields:
                wanted = [key]
            else:
                wanted = []
            for name in wanted:
                if name not in fields:
                    fields.add(name)
                    moved = True
    sections = []
    for section in form['sections']:
        kept_fields = [f for f in section.get('fields') or [] if f['key'] in fields]
        kept_blocks = [b for b in section.get('blocks') or [] if b in blocks]
        if kept_fields or kept_blocks:
            sections.append({**section, 'fields': kept_fields, 'blocks': kept_blocks})
    kept = {k: v for k, v in (form.get('blocks') or {}).items() if k in blocks}
    return {**form, 'sections': sections, 'blocks': kept, 'blank_pdf': '', 'narrowed': True}
