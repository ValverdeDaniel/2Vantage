"""`visible_if` and block gates (G14, G15). Pure.

Operators: nonempty, eq, ne, gt, gte. `ne` is true for a blank answer too: "shown until No is picked" is how the
carriers' own forms gate a section on a checkbox pair (Florida Blue's Q13, the SIIA "no risks" box).
"""

OPS = ('nonempty', 'eq', 'ne', 'gt', 'gte')


def number(value):
    """A typed number as a float, or None ($, % and thousands commas allowed)."""
    try:
        return float(str(value).replace(',', '').replace('$', '').replace('%', '').strip())
    except (TypeError, ValueError):
        return None


def condition_met(cond, values):
    """One `visible_if` clause against a flat {field key: value} dict (one row, or the scalars)."""
    if not cond:
        return True
    op = cond.get('op', 'nonempty')
    raw = values.get(cond.get('field', ''), '')
    text = ('' if raw is None else str(raw)).strip()
    if op == 'nonempty':
        return bool(text)
    if op == 'eq':
        return text == str(cond.get('value', ''))
    if op == 'ne':
        return text != str(cond.get('value', ''))
    if op in ('gt', 'gte'):
        left, right = number(text), number(cond.get('value'))
        if left is None or right is None:
            return False
        return left > right if op == 'gt' else left >= right
    return True


def block_visible(form, block_key, scalars):
    """Whether a repeating block applies at all, given the scalar answers (Florida Blue's condition grid is gated on
    Q16, its plans on Q13; the SIIA grid on "no risks")."""
    block = (form.get('blocks') or {}).get(block_key)
    if not block:
        return False
    return condition_met(block.get('visible_if'), scalars)
