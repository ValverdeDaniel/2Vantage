"""Which design rows a line's tabs show, and each value as the client reads it (plan.md §9.4; old `presentation_model`
`design_items` / `design_text` and `presentation_workbook.generic_design_items` at 891f1b3). Pure.

An item is {'id', 'kind': 'row'|'band', 'label', 'keys', 'pair', 'indent', 'inout'?}. The order is the house map's
for the line's field set, whatever order the producer picked the rows in; a row shows when a picked key has a value
on one of the line's plans (the RAW stored text, so a stored '0' counts); a band shows when one of its rows does. Every
other picked key with a value follows under "Other Plan Details". Only client fields are ever picked (catalog).
"""

from quotes import fields

from . import rows as house
from . import values


def _has_value(key, plans):
    return any(str(plan.values.get(key) if plan.values.get(key) is not None else '').strip() for plan in plans)


def _label(key):
    return fields.BY_KEY[key]['label'] if key in fields.BY_KEY else key


def _row_item(row, picked, plans):
    keys = tuple(key for key in row.keys if key in picked)
    if not keys or not any(_has_value(key, plans) for key in keys):
        return None
    item = {
        'id': row.keys[0],
        'kind': 'row',
        'label': row.label or _label(keys[0]),
        'keys': keys,
        'pair': row.flag == 'pair',
        'indent': 2 if row.flag == 'indent' else 1,
    }
    if row.flag == 'inout':
        item['inout'] = True
    return item


def _band_item(band_id, label):
    return {'id': f'band:{band_id}', 'kind': 'band', 'label': label, 'keys': (), 'pair': False, 'indent': 0}


def items(field_set, picked, plans, house_map=None):
    """The design items of a rates tab (or, with `house_map`, of the Compare and All Plans tabs)."""
    picked = list(picked)
    pick_set = set(picked)
    found, known = [], set()
    for entry in house_map or house.house_rows(field_set):
        if isinstance(entry, house.Band):
            inner = [item for item in (_row_item(row, pick_set, plans) for row in entry.rows) if item]
            known.update(key for row in entry.rows for key in row.keys)
            if inner:
                found.append(_band_item(entry.id, entry.label))
                found.extend(inner)
        else:
            known.update(entry.keys)
            item = _row_item(entry, pick_set, plans)
            if item:
                found.append(item)
    others = [key for key in picked if key not in known and key not in house.NEVER_DESIGN and _has_value(key, plans)]
    if others:
        found.append(_band_item('other', house.OTHER_BAND))
        found += [
            {'id': key, 'kind': 'row', 'label': _label(key), 'keys': (key,), 'pair': False, 'indent': 1}
            for key in others
        ]
    return found


def generic_items(picked, plans):
    """A generic tab's design rows, in the picked order: every picked key with a value on the line except the
    contribution rows (a generic tab has no block for them), the plan number (already on the Plan row) and the SBC
    link. The rates, the unit rate and the group premium print here as ordinary rows, a rate with its stored
    decimals."""
    skip = set(fields.CONTRIB_KEYS) | {'plan_number', values.SBC_KEY}
    return [
        {'id': key, 'kind': 'row', 'label': _label(key), 'keys': (key,), 'pair': False, 'indent': 1}
        for key in dict.fromkeys(picked)
        if key not in skip and _has_value(key, plans)
    ]


def text(item, plan):
    """A design value as the proposal prints it, always text, so a looked-up cell reads the same whichever plan is
    picked. An in/out row prints "in / out" with N/A for a side the plan does not state; a three-key pair (the Rx
    card) keeps a dash for a missing tier so the others never shift."""
    shown = [values.text(key, plan.values.get(key)) for key in item['keys']]
    if item.get('inout') and len(shown) == 2:
        inside, outside = shown
        if not inside and not outside:
            return ''
        return f'{inside or "N/A"} / {outside or "N/A"}'
    if item['pair']:
        if len(shown) > 2:
            return ' / '.join(part or '—' for part in shown) if any(shown) else ''
        return ' / '.join(part for part in shown if part)
    return shown[0] if shown else ''
