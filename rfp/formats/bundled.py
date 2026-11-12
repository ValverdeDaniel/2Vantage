"""The carriers' own workbooks, bundled byte for byte (plan.md Appendix A; K93, K96), and the drift guard.

`assets/carrier_templates/` holds the four census workbooks copied from old Vantage 891f1b3
`benefits/templates_xlsx/`; each must still hash to the SHA-256 recorded in the old `templates_xlsx/README.md` (Warner
Pacific sent them 2026-09-09 to 09-11; `warner_census.xlsx` is Warner's census sheet already cut out of their 2–50
request form, so the offline re-cut tool stays behind). `verify` proves a workbook still matches its definition: each
declared header is read at its COLUMN LETTER (these layouts repeat headers — "COVERAGE TYPE" four times — and merge
others), and each group-information label at its cell; a moved column fails the build by name instead of scattering a
roster into the wrong fields (the old `workbooks.verify_census_template`).
"""

import functools
import hashlib
from pathlib import Path

from rfp.xlsx.package import read_sheet
from rfp.xlsx.refs import FillError, col_index, col_letters

FOLDER = Path(__file__).resolve().parents[2] / 'assets' / 'carrier_templates'
SHA256 = {
    'warner_census.xlsx': '203219486188f3c53eb852a214a4631cf166df629f857f8d9f5566188cfe6981',
    'aetna_gateway_census.xlsx': 'dd04daca3e26989b4c7ac551f23b47faf2cbee9ba478fcbe7dbde15c8671cd99',
    'angle_census.xlsx': '018e71993386b97afc57e1c58cd9a8d5ba7abc071d4934c1843a0556b70863b4',
    'uhc_census.xlsx': '2a464a159d04053c18c1eb3a58c6cd83e58ce53be93ffb3143c86213d5242e2f',
}


def normalize(text):
    """Collapse the whitespace carrier headers carry: real newlines, U+2028 line separators (Angle's date header),
    non-breaking and double spaces."""
    return ' '.join(str(text or '').replace(' ', ' ').replace(' ', ' ').split())


@functools.lru_cache(maxsize=8)
def raw(name):
    path = FOLDER / name
    if not path.is_file():
        raise FillError(f'{name} is not bundled with the app.')
    return path.read_bytes()


def digest(name):
    return hashlib.sha256(raw(name)).hexdigest()


def letters(fmt):
    """Each column's letter on the carrier's own sheet."""
    origin = col_index(fmt['origin'])
    return [col_letters(origin + i) for i in range(len(fmt['columns']))]


def verify(fmt, src=None):
    """Raise FillError naming the cell when a header or label is not where the definition puts it."""
    src = raw(fmt['file']) if src is None else src
    sheet, shared = read_sheet(src, fmt['sheet'])
    for letter, column in zip(letters(fmt), fmt['columns'], strict=True):
        expected = normalize(column.get('header'))
        if not expected:  # a merged sub-column (Warner's "Last" cell)
            continue
        ref = f'{letter}{fmt["header_row"]}'
        found = normalize(sheet.text_at(ref, shared))
        if not found.startswith(expected[:40]):
            raise FillError(f'{fmt["file"]}: expected {ref} to start "{expected}", found "{found}"')
    for entry in fmt.get('group_info') or []:
        expected = normalize(entry.get('label'))
        if not entry.get('label_cell') or not expected:
            continue
        group_sheet, group_shared = read_sheet(src, entry.get('sheet') or fmt['sheet'])
        found = normalize(group_sheet.text_at(entry['label_cell'], group_shared))
        if not found.startswith(expected):
            raise FillError(f'{fmt["file"]}: expected {entry["label_cell"]} to start "{expected}", found "{found}"')
    return True
