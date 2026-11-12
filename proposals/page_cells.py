"""The benefit rows under each page's two cost rows, as formatted text (plan.md §9.4; F37, J16; J.5 B3, B17).

The Advisor's Columns tab picks the rows (Daniel, 2026-11-10: "the different categories of columns"), less the
board's derived columns, which the cost rows already say; All columns is every row of the line under its group's
heading. The builder's "Key rows" (`catalog.KEY_PRESET`, J16) are its field set's few rows, the Rx tiers as one.
Display only: the client files print every row. Only fields a client document may print are shown (§4.3 `client`),
so lasers never reach this view (J.5 B3); values read as the client files print them (`formatting.value`), so
"$797.50" never reads "$797.5" (B17). A row no shown plan has a value for is left out, as the old payload left it.
"""

from quotes import board_presets, fields

from . import catalog
from . import formatting as fmt

PRESETS = (*dict(board_presets.PRESETS), catalog.KEY_PRESET)


def keys(line, preset):
    """The field keys the preset shows as rows on the line, in its order (`catalog.RX_ROW` for the Rx tiers)."""
    if preset == catalog.KEY_PRESET:
        return catalog.key_rows(line)
    return [
        key
        for key in board_presets.columns(preset, line)
        if key not in board_presets.DERIVED_KEYS and fields.BY_KEY[key]['client']
    ]


def rows(line, preset, plans):
    """[{key, label, section, cells: {plan id: text}}] for `plans` (model rows); `section` names the row's group under
    All columns, and is '' otherwise."""
    groups = {group: label for group, label, _keys in fields.groups_for(line)}
    out = []
    for key in keys(line, preset):
        if key == catalog.RX_ROW:
            out.extend(_rx_row(plans))
            continue
        cells = {plan.id: fmt.value(key, plan.values.get(key)) for plan in plans}
        if not any(cells.values()):
            continue
        field = fields.BY_KEY[key]
        section = groups.get(field['group'], '') if preset == 'all' else ''
        out.append({'key': key, 'label': field['label'], 'section': section, 'cells': cells})
    return out


def _rx_row(plans):
    """The Rx tiers as one row, "$10 / $40 / $70 / 20%" (old keyRows.js); [] when no plan has one."""
    cells = {}
    for plan in plans:
        tiers = [fmt.value(key, plan.values.get(key)) for key in catalog.RX_TIER_KEYS]
        cells[plan.id] = ' / '.join(tier for tier in tiers if tier)
    if not any(cells.values()):
        return []
    return [{'key': catalog.RX_ROW, 'label': catalog.RX_LABEL, 'section': '', 'cells': cells}]
