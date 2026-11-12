"""An issue's packet: its stored files in one zip (plan.md §7.12; J96, J103; the old `pipeline/proposal_packet.py` at
891f1b3, simplified: the zip holds an issued version's stored bytes, never a fresh build).

The producer ticks which files go in (the packet card; a download preference kept in that browser, never on the deal),
sent as `?include=pdf,pptx,xlsx`. The internal spreadsheet is never a member: it prints every plan and the stop-loss
lasers, and a zip gets forwarded whole. The zip holds no README: a client should not read our warnings.
"""

import io
import zipfile

from deals.downloads import safe_filename

from .catalog import FILE_KEYS

INTERNAL = 'internal_xlsx'
INTERNAL_REFUSAL = (
    'The internal spreadsheet is never in the packet, because it is not for clients. Download it on its own.'
)
NOTHING_TICKED = 'Tick at least one file for the packet.'


class Refused(Exception):
    """The sentence the producer reads instead of a zip."""


def parse_include(raw):
    """The member keys asked for, in the card's order; refuses the internal spreadsheet by name, an unknown key and
    an empty list (the old sentences). No `include` at all means every file."""
    if raw is None:
        return list(FILE_KEYS)
    asked = {bit.strip() for bit in str(raw).split(',') if bit.strip()}
    if INTERNAL in asked:
        raise Refused(INTERNAL_REFUSAL)
    unknown = sorted(asked - set(FILE_KEYS))
    if unknown:
        raise Refused(f'Unknown packet file "{unknown[0]}".')
    if not asked:
        raise Refused(NOTHING_TICKED)
    return [key for key in FILE_KEYS if key in asked]


def zip_name(deal):
    """`<Client> - <year> Benefits Proposal.zip` (J104's stem, the old `packet_filename`)."""
    year = deal.effective_date.year if deal.effective_date else ''
    return safe_filename(f'{deal.client.name} - {year} Benefits Proposal.zip'.replace('  ', ' '))


def build(row, include):
    """The zip's bytes: each ticked file's stored bytes under its stored name."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for key in include:
            document = getattr(row, key)
            with document.file.open('rb') as handle:
                archive.writestr(document.original_name, handle.read())
    return buffer.getvalue()
