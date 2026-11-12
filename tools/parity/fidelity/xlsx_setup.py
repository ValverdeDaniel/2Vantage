"""A worksheet's settings compared (Q.5): frozen panes, zoom, gridlines, merges, drop-downs, conditional fills,
pictures and the print setup (orientation, paper, margins, centring, scale or Fit To, repeated rows and columns, the
print area, manual breaks, header and footer with their Draft stamp masked). Ranges are read through the alignment.

`differences(title, old_ws, new_ws, maps, removed, added)` → [(where, kind, old, new)].
"""

from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

from . import mask, refs


def _moved_cell(ref, rmap, cmap):
    letters, row = coordinate_from_string(ref)
    col = column_index_from_string(letters)
    return f'{get_column_letter(cmap.get(col, col))}{rmap.get(row, row)}'


def _freeze(ws):
    return ws.freeze_panes or None


def _merges(ws, title, maps, inserted):
    """The sheet's merges (read through `maps`), less those wholly inside a row or column `inserted` holds (rows,
    columns): a merge on an added or removed row is part of that row's difference, reported once."""
    rows, cols = inserted
    found = set()
    for rng in ws.merged_cells.ranges:
        if all(r in rows for r in range(rng.min_row, rng.max_row + 1)) or all(
            c in cols for c in range(rng.min_col, rng.max_col + 1)
        ):
            continue
        found.add(refs.translate(str(rng), title, maps) if maps else str(rng))
    return found


def _validations(ws, title, maps):
    found = {}
    for dv in ws.data_validations.dataValidation:
        sqref = ' '.join(refs.translate(str(r), title, maps) if maps else str(r) for r in dv.sqref.ranges)
        formula = refs.translate(dv.formula1, title, maps) if maps else dv.formula1
        found[sqref] = (dv.type, formula, dv.promptTitle, dv.prompt, dv.errorTitle, dv.error, dv.errorStyle or 'stop')
    return found


def _fills(ws, title, maps):
    found = {}
    for rng in ws.conditional_formatting:
        sqref = ' '.join(refs.translate(str(r), title, maps) if maps else str(r) for r in rng.sqref.ranges)
        rules = []
        for rule in sorted(rng.rules, key=lambda r: r.priority or 0):
            formula = [refs.translate(f, title, maps) if maps else f for f in (rule.formula or [])]
            fill = getattr(getattr(rule, 'dxf', None), 'fill', None)
            colour = None
            if fill is not None:
                colour = (getattr(fill.bgColor, 'rgb', None) or getattr(fill.fgColor, 'rgb', None) or '')[-6:]
            rules.append((rule.type, tuple(formula), bool(rule.stopIfTrue), colour))
        found[sqref] = tuple(rules)
    return found


def _images(ws, maps_here):
    rmap, cmap = maps_here
    out = []
    for image in getattr(ws, '_images', []):
        anchor = getattr(image.anchor, '_from', None)
        cell = (anchor.row + 1, anchor.col + 1) if anchor is not None else (0, 0)
        out.append((cell if maps_here is None else (rmap.get(cell[0], cell[0]), cmap.get(cell[1], cell[1])),
                    int(image.width), int(image.height)))  # fmt: skip
    return sorted(out)


def _print(ws, title, maps):
    rmap, cmap = maps.get(title, ({}, {})) if maps else ({}, {})
    setup, margins = ws.page_setup, ws.page_margins
    fit = ws.sheet_properties.pageSetUpPr
    uses_fit = bool(fit is not None and fit.fitToPage)
    area = ws.print_area
    area = (area if isinstance(area, str) else ','.join(area or [])) or None
    return {
        'orientation': setup.orientation,
        'paper': str(setup.paperSize) if setup.paperSize is not None else None,
        'margins': tuple(round(float(getattr(margins, side) or 0), 3) for side in ('left', 'right', 'top', 'bottom')),
        'centred across': bool(ws.print_options.horizontalCentered),
        'scale': None if uses_fit else int(setup.scale or 100),
        'fit to': (
            int(setup.fitToWidth if setup.fitToWidth is not None else 1),
            int(setup.fitToHeight if setup.fitToHeight is not None else 1),
        )
        if uses_fit
        else None,  # fmt: skip
        'repeated rows': refs.rows_span(ws.print_title_rows, rmap) if maps else ws.print_title_rows,
        'repeated columns': refs.cols_span(ws.print_title_cols, cmap) if maps else ws.print_title_cols,
        'print area': refs.translate(area, title, maps) if maps and area else area,
        'column breaks': sorted(cmap.get(b.id, b.id) if maps else b.id for b in ws.col_breaks.brk),
        'row breaks': sorted(rmap.get(b.id, b.id) if maps else b.id for b in ws.row_breaks.brk),
        'header': mask.text(ws.oddHeader.center.text or '') or None,
        'footer': mask.text(ws.oddFooter.center.text or '') or None,
    }


def differences(title, old_ws, new_ws, maps, removed=((), ()), added=((), ())):
    """`removed` and `added`: the (rows, columns) only the old or only the new sheet has, by their own numbers."""
    out = []
    rmap, cmap = maps.get(title, ({}, {}))
    old_freeze = _freeze(old_ws)
    if old_freeze:
        old_freeze = _moved_cell(old_freeze, rmap, cmap)
    if old_freeze != _freeze(new_ws):
        out.append(('frozen panes', 'freeze', old_freeze, _freeze(new_ws)))
    if (old_ws.sheet_view.zoomScale or 100) != (new_ws.sheet_view.zoomScale or 100):
        out.append(('zoom', 'zoom', old_ws.sheet_view.zoomScale, new_ws.sheet_view.zoomScale))
    if (old_ws.sheet_view.showGridLines is not False) != (new_ws.sheet_view.showGridLines is not False):
        out.append(('gridlines', 'gridlines', old_ws.sheet_view.showGridLines, new_ws.sheet_view.showGridLines))
    old_merges, new_merges = _merges(old_ws, title, maps, removed), _merges(new_ws, title, None, added)
    for rng in sorted(old_merges - new_merges):
        out.append((rng, 'merge-removed', rng, None))
    for rng in sorted(new_merges - old_merges):
        out.append((rng, 'merge-added', None, rng))
    old_dv, new_dv = _validations(old_ws, title, maps), _validations(new_ws, title, None)
    for sqref in sorted(set(old_dv) | set(new_dv)):
        if old_dv.get(sqref) != new_dv.get(sqref):
            out.append((sqref, 'drop-down', old_dv.get(sqref), new_dv.get(sqref)))
    old_cf, new_cf = _fills(old_ws, title, maps), _fills(new_ws, title, None)
    for sqref in sorted(set(old_cf) | set(new_cf)):
        if old_cf.get(sqref) != new_cf.get(sqref):
            out.append((sqref, 'conditional-fill', old_cf.get(sqref), new_cf.get(sqref)))
    if _images(old_ws, (rmap, cmap)) != _images(new_ws, ({}, {})):
        out.append(('pictures', 'picture', _images(old_ws, (rmap, cmap)), _images(new_ws, ({}, {}))))
    old_print, new_print = _print(old_ws, title, maps), _print(new_ws, title, None)
    for key, before in old_print.items():
        if before != new_print[key]:
            out.append((f'print {key}', 'print', before, new_print[key]))
    return out
