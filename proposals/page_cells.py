"""The benefit rows under each page's two cost rows, as formatted text (plan.md §9.4; F37, J16; J.5 B3, B17).

The Advisor's Columns tab picks the rows (Daniel, 2026-11-10: "the different categories of columns"), less the
board's derived columns, which the cost rows already say; All columns is every row of the line under its group's
heading. Display only: the client files print every row. Only fields a client document may print are shown (§4.3
`client`), so lasers never reach this view (J.5 B3); values read as the client files print them (`formatting.value`),
so "$797.50" never reads "$797.5" (B17). A row no shown plan has a value for is left out, as the old payload left it.
"""

from quotes import board_presets, fields

from . import formatting as fmt


def keys(line, preset):
    """The field keys the preset shows as rows on the line, in its order."""
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
        cells = {plan.id: fmt.value(key, plan.values.get(key)) for plan in plans}
        if not any(cells.values()):
            continue
        field = fields.BY_KEY[key]
        section = groups.get(field['group'], '') if preset == 'all' else ''
        out.append({'key': key, 'label': field['label'], 'section': section, 'cells': cells})
    return out
