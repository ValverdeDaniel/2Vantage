"""Who opened a file that carries member data, and the name it downloads under (plan.md §3.6, §3.8; E99, Q.8).

A file of a PHI kind, or one the member-data screen found people in, writes a `downloaded` or `viewed` row through
`deals.activity.log_access`: the document id and the kind, never the file's name; views coalesce per file; the rows
never move "Last updated". Such a file downloads as "<Client> - <Kind>.<ext>", never under the name it came with.
"""

from deals import activity
from deals.downloads import safe_filename

from .. import kinds, screening


def carries_members(document):
    return document.kind in kinds.PHI_KINDS or screening.lists_members(document)


def record_access(user, document, inline=False):
    """Log a download (or, with `inline`, a view) of a file that carries member data; any other file logs nothing."""
    if not carries_members(document):
        return None
    action = 'viewed' if inline else 'downloaded'
    return activity.log_access(document.deal, user, action, f'a {kinds.label(document.kind)} file', document.id)


def download_name(document):
    if not carries_members(document):
        return document.original_name
    extension = kinds.extension(document.original_name)
    return safe_filename(f'{document.deal.client.name} - {kinds.label(document.kind)}') + extension
