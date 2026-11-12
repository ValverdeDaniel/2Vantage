"""File responses with the headers of plan.md §3.6 and §3.8. Shared by every app that serves a file (O.3.5).

- The content type comes from an explicit map by extension (K63, E17), never from the upload and never from Python's
  `mimetypes`, which differs between machines; an unknown extension is `application/octet-stream`.
- `Content-Disposition: attachment`, or `inline` for the viewer, under a sandbox CSP so an inline file can never run
  as a page (E17); `X-Content-Type-Options: nosniff`; `Cache-Control: private, no-store`. Never compressed.
- The body streams in chunks (FileResponse), so a large zip or `.eml` never meets Cloud Run's 32 MiB limit (K.5 #39).
"""

import os
import re

from django.http import FileResponse

_UNSAFE = re.compile(r'[^A-Za-z0-9 ._-]')

CONTENT_TYPES = {
    '.pdf': 'application/pdf',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xlsm': 'application/vnd.ms-excel.sheet.macroEnabled.12',
    '.xls': 'application/vnd.ms-excel',
    '.csv': 'text/csv',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.doc': 'application/msword',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.zip': 'application/zip',
    '.eml': 'message/rfc822',
    '.msg': 'application/vnd.ms-outlook',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.txt': 'text/plain',
}
DEFAULT_TYPE = 'application/octet-stream'
SANDBOX = "default-src 'none'; sandbox"  # the old app's header (docscan/serving.py)


def safe_filename(name):
    cleaned = _UNSAFE.sub('', name).strip(' .')
    return cleaned or 'download'


def content_type_for(filename):
    return CONTENT_TYPES.get(os.path.splitext(filename or '')[1].lower(), DEFAULT_TYPE)


def file_response(fileobj, filename, inline=False):
    """Stream a file under `filename` (made safe here); the content type comes from its extension."""
    filename = safe_filename(filename)
    response = FileResponse(fileobj, content_type=content_type_for(filename))
    disposition = 'inline' if inline else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    if inline:
        response['Content-Security-Policy'] = SANDBOX
    return response
