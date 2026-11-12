"""The dependent pickers (G12), effects (G13) and the SIC pair (G16). Pure.

A dependent picker's options come from a table keyed by its parent's answer, through the form's aliases: three labels
on Florida Blue's form match no branch of the carrier's own change script, so each is mapped onto the branch its author
meant. The field names its alias table (`alias`), and a block names the fields that drive its effects
(`effect_drivers`), so no carrier's field names live here (P1). An empty option list hides the field.
"""

from .spec import field_spec, get_block


def alias(form, kind, text):
    """A picker label resolved onto the table key that matches it."""
    return ((form.get('aliases') or {}).get(kind) or {}).get(text, text)


def _parent(form, field, values):
    parent = str(values.get(field['depends_on'], '') or '').strip()
    return alias(form, field.get('alias', ''), parent) if parent else ''


def option_key(form, block_key, values, field_key):
    """'<table>/<parent>' for a dependent picker with a parent answered (the browser reads the options out of the
    spec's tables by it), else ''."""
    field = field_spec(form, block_key, field_key)
    if not field or not field.get('depends_on'):
        return ''
    parent = _parent(form, field, values)
    return f'{field["options_from"]}/{parent}' if parent else ''


def flat_options(form, field):
    """A plain table's options: a list of labels, or one column of a (code, description) table — codes in the
    carrier's order, descriptions alphabetical, each once, as the source form presents each picker (G17)."""
    table = (form.get('tables') or {}).get(field.get('options_from') or '')
    if not table:
        return []
    if not isinstance(table[0], (tuple, list)):
        return list(table)
    index = 1 if field.get('option_mode') == 'description' else 0
    seen = list(dict.fromkeys(row[index] for row in table))
    return sorted(seen) if index == 1 else seen


def resolve_options(form, block_key, values, field_key):
    """The options a choice field offers now, given its row's other answers; [] for a dependent picker with nothing
    to offer (which also hides it)."""
    field = field_spec(form, block_key, field_key)
    if not field:
        return []
    if field.get('options'):
        return list(field['options'])
    if not field.get('options_from'):
        return []
    if field.get('depends_on'):
        parent = _parent(form, field, values)
        table = (form.get('tables') or {}).get(field['options_from']) or {}
        return list(table.get(parent) or []) if parent else []
    return flat_options(form, field)


def active_effects(form, block_key, values):
    """{flag: on} for one row, faithful to the carrier's two change scripts: a category sets the flags; a condition
    then re-decides only the flags its own script clears on every change (`condition_overrides`: surgery and cancer
    counts on Florida Blue's form). Transplant is not cleared there, so a category's transplant flag survives naming a
    specific transplant. A row with no category shows the template's initial flags (the cancer-count pair)."""
    block = get_block(form, block_key) or {}
    drivers = block.get('effect_drivers')
    if not drivers:
        return {}
    tables = form.get('tables') or {}
    category = alias(form, 'category', str(values.get(drivers['category'], '') or '').strip())
    condition = alias(form, 'condition', str(values.get(drivers['condition'], '') or '').strip())
    if not category:
        return {flag: True for flag in tables.get('initial_effects') or ()}
    effects = dict((tables.get('category_effects') or {}).get(category) or {})
    if condition:
        overrides = set(tables.get('condition_overrides') or ())
        from_condition = (tables.get('condition_effects') or {}).get(condition) or {}
        for flag in overrides:
            effects[flag] = bool(from_condition.get(flag))
        for flag, on in from_condition.items():
            if flag not in overrides and on:
                effects[flag] = True
    return effects


def paired_value(form, block_key, field_key, text):
    """The other half of a (code, description) pair for a field with `pair_with`, or None when unresolvable; '' maps
    to '' (clearing one clears the other). A duplicate description resolves to the first code in the carrier's order,
    the row the carrier form's one shared data node shows (G16)."""
    field = field_spec(form, block_key, field_key)
    if not field or not field.get('pair_with'):
        return None
    table = (form.get('tables') or {}).get(field.get('options_from') or '')
    if not table or not isinstance(table[0], (tuple, list)):
        return None
    value = ('' if text is None else str(text)).strip()
    if not value:
        return ''
    source, target = (1, 0) if field.get('option_mode') == 'description' else (0, 1)
    return next((row[target] for row in table if row[source] == value), None)
