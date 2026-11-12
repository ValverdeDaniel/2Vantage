"""Navigating a form spec (G.6). A spec is plain dicts: {key, version, kind, title, sections: [{key, number, label,
intro?, legend?, fields: [...], blocks: [block key]}], blocks: {key: {label, row_label, add_label, min_rows, max_rows,
visible_if?, rows_from?, sensitive?, fields: [...]}}, tables, aliases}. Block '' means the scalar fields that live on
the sections."""


def get_block(form, block_key):
    """A repeating block's spec, or None ('' is the scalars)."""
    if not block_key:
        return None
    return (form.get('blocks') or {}).get(block_key)


def block_keys(form):
    return list((form.get('blocks') or {}).keys())


def section_fields(form):
    """Every scalar field across the sections, in display order."""
    return [field for section in form['sections'] for field in section.get('fields') or []]


def block_fields(form, block_key):
    block = get_block(form, block_key)
    return list(block.get('fields') or []) if block else []


def fields_for(form, block_key):
    return block_fields(form, block_key) if block_key else section_fields(form)


def field_spec(form, block_key, field_key):
    for field in fields_for(form, block_key):
        if field['key'] == field_key:
            return field
    return None


def all_field_refs(form):
    """[(block key, field spec)] over the whole form: scalars, then each block's fields."""
    refs = [('', field) for field in section_fields(form)]
    for key in block_keys(form):
        refs.extend((key, field) for field in block_fields(form, key))
    return refs
