"""File responses with the headers of plan.md §3.6 and §3.8. Shared by every app that serves a file."""

import mimetypes
import re

from django.http import FileResponse

_UNSAFE = re.compile(r'[^A-Za-z0-9 ._-]')


def safe_filename(name):
    cleaned = _UNSAFE.sub('', name).strip(' .')
    return cleaned or 'download'


def content_type_for(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def file_response(fileobj, filename, inline=False):
    """Stream a file; the content type comes from the extension, never from an upload."""
    filename = safe_filename(filename)
    response = FileResponse(fileobj, content_type=content_type_for(filename))
    disposition = 'inline' if inline else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response
