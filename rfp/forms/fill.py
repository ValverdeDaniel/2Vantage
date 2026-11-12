"""Warner's quote request form, filled from one request (plan.md §9.9; K42, K99–K101). Never stored.

The file Warner opens must be their own form, filled the way a person fills it in Excel (old 891f1b3
`pipeline/quote_request_form.py`): dates as dates, counts as numbers, the commission as text, nothing added, merged or
resized. Before a value is written, every label beside an input cell is checked against the map (`verify`): a moved
row fails the build by name instead of writing the group's name into the wrong cell.

- The header: the group facts and the broker block (`printed.form_facts`), the band's enrolled count (K17, bug 38) and
  the SIC code as Nature of Business (OQ62).
- 2–50 and 51+ only: the funding boxes (2–50 has no ASO box, so asking for ASO warns), the carrier × line matrix where
  the form has a box (a bare TRUE in a hatched cell would print the word), the Notes cell with wrap on (what Alt+Enter
  leaves; the row keeps Warner's height) and the Additional Carriers line (typed-in names and those the matrix lacks).
- `census=True` prints the roster on Warner's census sheet from the universal census's rows (`rfp.formats`, the same
  columns and typing as the Warner census file), up to Warner's 500-row counter (K42); the packet's copy is header
  only (K99), so the roster never travels twice.
"""

import functools
import hashlib
from collections import namedtuple

from deals import carriers as identities

from .. import carriers, printed, words
from ..formats import bundled, definitions, rows, translate
from ..formats.fill import saved_by
from ..xlsx import package
from ..xlsx.refs import FillError, col_index, col_letters
from . import maps

File = namedtuple('File', 'content filename warnings')


@functools.lru_cache(maxsize=4)
def raw(variant):
    path = maps.FOLDER / maps.VARIANTS[variant]['file']
    if not path.is_file():
        raise FillError(f'{path.name} is not bundled with the app.')
    return path.read_bytes()


def digest(variant):
    return hashlib.sha256(raw(variant)).hexdigest()


def verify(variant, src=None):
    """Raise FillError naming the cell when a label is not where the map puts it."""
    spec = maps.VARIANTS[variant]
    sheet, shared = package.read_sheet(raw(variant) if src is None else src, spec['sheet'])
    for label_cell, expected, _cell, _source in spec['header']:
        found = bundled.normalize(sheet.text_at(label_cell, shared))
        if not found.startswith(expected):
            raise FillError(f'{spec["file"]}: expected {label_cell} to start "{expected}", found "{found}"')
    return True


def census_layout(variant):
    """The universal census format at this form's geometry: the same columns on Warner's own census sheet."""
    spec, fmt = maps.VARIANTS[variant]['census'], definitions.DEFINITIONS[definitions.UNIVERSAL]
    geometry = {'sheet': spec['sheet'], 'header_row': spec['header_row'], 'data_row': spec['data_row']}
    return {**fmt, **geometry, 'origin': spec['origin_col'], 'clear': spec['clear'], 'max_rows': spec['max_rows']}


def _census(ctx, variant):
    """(writes, warnings) for the roster inside the form."""
    layout = census_layout(variant)
    built = rows.build(layout, ctx.people, ctx.lines, ctx.deal.effective_date)
    origin = col_index(layout['origin'])
    writes = {}
    for r, values in enumerate(built.rows[: layout['max_rows']]):
        for c, value in enumerate(values):
            typed = translate.typed(layout['columns'][c], value)
            if typed not in (None, ''):
                writes[f'{col_letters(origin + c)}{layout["data_row"] + r}'] = typed
    return writes, list(built.warnings)


def _matrix(ctx, spec):
    """A carrier × line box ticked only where the form has one, for a picked carrier quoting a requested line."""
    writes = {}
    wanted = set(ctx.lines)
    for key in ctx.picked:
        grid = spec['matrix'].get(identities.BY_KEY[key]['group'])
        if not grid or key not in grid['rows']:
            continue  # off the form (Trustmark): it rides the Additional Carriers line
        for column in carriers.columns_for(key, ctx.band):
            letter = grid['cols'].get(column)
            if letter and wanted & set(carriers.COLUMN_LINES.get(column, ())):
                writes[f'{letter}{grid["rows"][key]}'] = True
    return writes


def _funding(ctx, spec):
    writes, warnings = {}, []
    for key in ctx.funding:
        cell = spec['funding_cells'].get(key)
        if cell:
            writes[cell] = True
        elif spec['funding_cells']:
            label = words.funding_labels([key])[0]
            warnings.append(f'{spec["label"]} has no box for "{label}" — say so in the email.')
    return writes, warnings


def funding_warnings(ctx, variant):
    """What the form cannot say about the funding asked (2–50 has no ASO box): the check lists it (K74's row level)."""
    return _funding(ctx, maps.VARIANTS[variant])[1]


def build(ctx, variant=None, census=False):
    """File(bytes, file name, warnings). Raises FillError when the bundled form no longer matches its map."""
    variant = variant or ctx.variant
    spec = maps.VARIANTS[variant]
    src = raw(variant)
    verify(variant, src)
    facts = printed.form_facts(ctx)
    writes = {cell: facts.get(source) for _label, _expected, cell, source in spec['header']}
    writes = {cell: value for cell, value in writes.items() if value not in ('', None)}
    boxes, warnings = _funding(ctx, spec)
    writes.update(boxes)
    writes.update(_matrix(ctx, spec))
    clones, styles = {}, {}
    notes = spec.get('notes')
    body = words.request_summary(ctx, on_form=True) if notes else ''
    if body:
        writes[notes['cell']] = f'{notes["prefix"]}{body}'
        sheet, _shared = package.read_sheet(src, spec['sheet'])
        base = sheet.style_of(notes['cell'])
        if base is not None:
            clones['notes'] = (base, dict(maps.WRAPPED))
            styles[notes['cell']] = 'notes'
    extra = ([ctx.other_text()] if ctx.other_text() else []) + words.off_form(ctx)
    if spec['additional_cell'] and extra:
        writes[spec['additional_cell']] = spec['additional_prefix'] + ', '.join(extra)
    edits = {spec['sheet']: {'writes': writes, 'styles': styles}}
    if census:
        bundled.verify(census_layout(variant), src)  # Warner's census sheet still has the universal census's columns
        roster, census_warnings = _census(ctx, variant)
        warnings += census_warnings
        layout = census_layout(variant)
        target = edits.setdefault(layout['sheet'], {})
        target.setdefault('writes', {}).update(roster)
        target['clear'] = list(layout['clear'])  # Warner's worked example goes only when a roster replaces it
        target['style_source_row'] = layout['data_row']
    content, fill_warnings = package.fill(src, edits, style_clones=clones, modified_by=saved_by(ctx.deal))
    return File(content, filename(ctx, variant, census), warnings + fill_warnings)


def filename(ctx, variant, census=False):
    """`<Client> - Quote request form[ - small group][ with census].xlsx`: no person's name, ever."""
    tail = ' with census' if census else ''
    return f'{ctx.deal.client.name} - Quote request form{maps.NAME_PART[variant]}{tail}.xlsx'
