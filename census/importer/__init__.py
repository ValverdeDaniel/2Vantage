"""Importing a census file (plan.md §5.3.2; C12–C16). Pure modules, one idea each:

- `words`: the header synonyms, tier spellings and waiver words (§4.2, §4.8; a data module);
- `read`: the file into a table — sheet, header row, data rows with their sheet row numbers, samples;
- `mapping`: the proposed column mapping and the member's changes to it;
- `people`: the people of a mapped table, masked SSNs restored, dependents linked.
The reformat of a one-row-per-benefit file is `census.pivot`; matching to the roster is `census.matching`.
`open_table` puts read and pivot together for an import's stored choices.
"""

from collections import namedtuple

from .. import pivot
from .read import NO_HEADER, CensusFileError, find_header_row, sheet_grids, table

# names: the workbook's sheets; table: what is mapped (reformatted when the recipe applies); recipe: the reformat's
# recipe (stored) and conflicts (things worth checking, read from the file each time, never stored: they name people).
Opened = namedtuple('Opened', 'names sheet header_row first_data_row table recipe conflicts')

__all__ = ['CensusFileError', 'Opened', 'open_table']


def _first_with_header(filename, raw, names):
    """The first sheet after the first one whose top rows hold a header (a workbook that opens on its instructions)."""
    for name in names[1:]:
        _names, chosen, rows = sheet_grids(filename, raw, name)
        header = find_header_row(rows)
        if header:
            return chosen, rows, header
    return None, None, None


def open_table(filename, raw, sheet=None, header_row=None, first_data_row=None, reformat=True):
    """The table an import maps: the chosen sheet (default the first, else the first with a header row), the header
    row (default the detected one), the first data row (default the row below), reformatted from one row per benefit
    unless `reformat` is False."""
    names, chosen, rows = sheet_grids(filename, raw, sheet)
    header = header_row or find_header_row(rows)
    if header is None and not sheet:
        chosen, rows, header = _first_with_header(filename, raw, names)
    if header is None:
        raise CensusFileError(NO_HEADER)
    first = first_data_row or header + 1
    found = table(chosen, rows, header, first)
    shaped, recipe, conflicts = pivot.reshape(found, reformat)
    return Opened(names, chosen, header, first, shaped, recipe, conflicts)
