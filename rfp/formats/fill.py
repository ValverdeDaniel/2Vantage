"""One carrier census file, built from the deal (plan.md §9.8 "Writing"; K90–K93, K97). Never stored.

`build(deal, file_key)` reads the live people once (`census.facts.people`), builds the format's rows (`rows.build`),
types each shown value for its cell (`translate.typed`: dates as dates, numbers as numbers, the carrier's Text cells
keep text) and fills the carrier's own bundled workbook in place (`rfp.xlsx.package.fill`): the worked-example people
cleared (Warner's "Ex:" rows, Aetna's row 4, Angle's Jane Doe), the roster from the data row, new cells styled from
the nearest data row, the group-information cells (UHC's Group Info tab, Aetna's J1 selector) from `rfp.printed`, the
recalculation flag only when a formula on a written sheet reads a written column (UHC), the file "last saved by" the
deal's agent as Excel records the person who filled it, and Aetna's stale thumbnail dropped.

A roster past the template's rows stops at the cap with a truthful warning (K97, OQ61). Angle's CSV (`angle-csv`) is
the workbook filled with everyone, saved as Excel saves "CSV UTF-8" (K91), and its text that begins like a formula goes
out behind an apostrophe, counted in one warning (K107). A file that cannot be built raises `FillError`; a deal with no
census raises `NoCensus` (K41).
"""

from collections import namedtuple

from census import facts as census_facts
from deals import rules as deal_rules
from deals.models import AgencySettings
from rfp import printed
from rfp.xlsx import as_csv, package
from rfp.xlsx.refs import col_index, col_letters

from . import bundled, definitions, rows, translate

File = namedtuple('File', 'content filename warnings built')
CSV_SUFFIX = '-csv'


class NoCensus(Exception):
    """The deal has nobody on its census: there is no file to build (K41)."""


class UnknownFile(Exception):
    """Not a census file key."""


def resolve(file_key):
    """(definition, 'xlsx' | 'csv') for `warner`, `aetna`, `angle`, `angle-csv` or `uhc`; raises UnknownFile."""
    base, kind = (file_key[: -len(CSV_SUFFIX)], 'csv') if file_key.endswith(CSV_SUFFIX) else (file_key, 'xlsx')
    found = definitions.BY_FILE_KEY.get(base)
    if found is None or kind not in found['formats']:
        raise UnknownFile(file_key)
    return found, kind


def file_keys():
    """Every census file key, primary format first, in definition order."""
    return [
        found['file_key'] + ('' if kind == found['formats'][0] else f'-{kind}')
        for found in definitions.DEFINITIONS.values()
        for kind in found['formats']
    ]


def filename(deal, fmt, kind):
    return f'{deal.client.name} - {fmt["carrier"]} census.{kind}'


def saved_by(deal):
    """Who the filled workbook says last saved it: the deal's agent, else the agency."""
    agency = AgencySettings.get()
    return deal_rules.agent_name(deal, agency) or agency.name or 'Vantage'


def _writes(fmt, built, limit):
    origin = col_index(fmt['origin'])
    out = {}
    for r, values in enumerate(built.rows[:limit]):
        for c, value in enumerate(values):
            typed = translate.typed(fmt['columns'][c], value)
            if typed is None or typed == '':
                continue
            out[f'{col_letters(origin + c)}{fmt["data_row"] + r}'] = typed
    return out


def _edits(deal, fmt, built, limit):
    edits = {fmt['sheet']: {'writes': _writes(fmt, built, limit), 'clear': list(fmt['clear']), 'style_source_row':
                            fmt['data_row']}}  # fmt: skip
    if fmt.get('group_info'):
        facts = printed.facts(deal)
        for entry in fmt['group_info']:
            value = facts.get(entry['source'])
            if value in ('', None):
                continue
            edits.setdefault(entry.get('sheet') or fmt['sheet'], {}).setdefault('writes', {})[entry['cell']] = value
    return edits


def build_rows(deal, fmt, people=None):
    """The format's rows for the deal (what the lens shows and the file holds)."""
    found = census_facts.people(deal.id) if people is None else people
    return rows.build(fmt, found, deal.requested_lines or [], deal.effective_date)


def build(deal, file_key, people=None):
    """File(bytes, filename, warnings, built rows). Raises UnknownFile, NoCensus or FillError."""
    fmt, kind = resolve(file_key)
    built = build_rows(deal, fmt, people)
    if not built.rows:
        raise NoCensus(file_key)
    src = bundled.raw(fmt['file'])
    bundled.verify(fmt, src)
    limit = None if kind == 'csv' else (fmt['max_rows'] or None)
    content, fill_warnings = package.fill(
        src,
        _edits(deal, fmt, built, limit),
        full_calc_on_load='auto',
        modified_by=saved_by(deal),
        drop_parts=['docProps/thumbnail.emf'],
    )
    warnings = list(built.warnings)
    if kind == 'csv':
        warnings = [text for text in warnings if text != rows.overflow_text(fmt, len(built.rows))]
        content, fenced = as_csv.sheet_to_csv(content, fmt['sheet'])
        if fenced:
            count = len(fenced)
            warnings.append(
                f'{count} census {"value starts" if count == 1 else "values start"} with =, +, - or @, so the CSV '
                'carries them as text behind a leading apostrophe (a spreadsheet would otherwise run them as '
                'formulas). Check those cells on the deal before uploading.'
            )
    return File(content, filename(deal, fmt, kind), warnings + fill_warnings, built)
