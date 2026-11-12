"""The RFP packet: everything ticked, in one zip (plan.md §9.10; K34–K56, K103). Never stored.

`<Client> - RFP packet - <YYYY-MM-DD>.zip` holds exactly the rows the grid shows ticked (`cards.packet.in_packet`):
the files the app builds at the top, and the documents from the file (attachments and the issued proposal) under
`Documents/`, a repeated name suffixed " (2)". `README.txt` lists the files, the lines and funding asked and the notes,
signed with the agency's name, and names no carrier (K103, bug 21); `Quote request summary.txt` rides only on the
Warner route, where naming the carriers is the point (bug 23). Both are written with a BOM, so Notepad shows the dashes.
Nothing ticked is refused (400); a row that cannot be built refuses the whole download by its label (409, K55).
"""

import io
import zipfile

from . import members as built
from . import words
from .cards import packet as cards

DOCUMENTS = 'Documents/'
SUMMARY = 'Quote request summary.txt'
README = 'README.txt'
FROM_THE_FILE = ('attachments',)
NOTHING = 'Nothing is ticked for the packet — choose at least one document.'


class Nothing(Exception):
    """No row is ticked (400)."""


def _path(row, member):
    if row['section'] in FROM_THE_FILE or row['key'] == 'proposal':
        return f'{DOCUMENTS}{member.name}'
    return member.name


def build(ctx, rows, today):
    """(zip bytes, file name, the members) for the ticked rows. Raises Nothing or members.NotBuilt."""
    wanted = cards.in_packet(rows)
    if not wanted:
        raise Nothing(NOTHING)
    found = built.members(ctx, wanted)
    paths = [_path(row, member) for row, member in zip(wanted, found, strict=True)]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, member in zip(paths, found, strict=True):
            archive.writestr(path, member.data)
        if ctx.route != 'direct':
            summary = words.summary_file(ctx)
            if summary:
                archive.writestr(SUMMARY, summary.encode('utf-8-sig'))
        names = [(path, member.title) for path, member in zip(paths, found, strict=True)]
        archive.writestr(README, words.readme(ctx, names, today).encode('utf-8-sig'))
    return buffer.getvalue(), filename(ctx, today), found


def filename(ctx, today):
    return f'{ctx.deal.client.name} - RFP packet - {today.isoformat()}.zip'
