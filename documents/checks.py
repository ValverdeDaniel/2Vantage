"""What an upload must pass before anything is stored (plan.md §3.8; E6, E7; OQ24).

One file per request; the kind is required and known; the extension is on the kind's accept list; the file's first
bytes are what its extension says (a renamed .exe is refused); at most `FILE_UPLOAD_MAX_BYTES` (30 MB, under Cloud
Run's 32 MiB request limit). Each refusal is a sentence the screen shows as it is; none repeats the file's name.
"""

from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError

from . import kinds

HEAD_BYTES = 8192

ZIP = b'PK\x03\x04'
OLE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'  # .xls, .doc and .msg: the old Office container
PNG = b'\x89PNG\r\n\x1a\n'
JPEG = b'\xff\xd8\xff'
TEXT = ('.csv', '.txt', '.eml')


class FileTooLarge(APIException):
    status_code = 413
    default_code = 'too_large'

    def __init__(self):
        megabytes = settings.FILE_UPLOAD_MAX_BYTES // (1024 * 1024)
        super().__init__(f'Files can be up to {megabytes} MB.')


def _starts_like(extension, head):
    if extension == '.pdf':
        return b'%PDF-' in head[:1024]  # a PDF's header may follow a little junk (the spec allows 1 KB)
    if extension in ('.xlsx', '.xlsm', '.docx', '.pptx'):
        return head.startswith(ZIP)
    if extension in ('.xls', '.doc', '.msg'):
        return head.startswith(OLE)
    if extension == '.png':
        return head.startswith(PNG)
    if extension in ('.jpg', '.jpeg'):
        return head.startswith(JPEG)
    if extension in TEXT:
        return b'\x00' not in head and not head.startswith((ZIP, OLE, PNG, JPEG, b'%PDF-', b'MZ'))
    return False


def matches_extension(filename, head):
    """Whether a file's first bytes are what its extension says (E7)."""
    return _starts_like(kinds.extension(filename), head or b'')


def read_head(upload):
    upload.seek(0)
    head = upload.read(HEAD_BYTES)
    upload.seek(0)
    return head


def check_kind(kind):
    if not kind:
        raise ValidationError({'kind': ['Choose what kind of document this is.']})
    if kind not in kinds.KIND_KEYS:
        raise ValidationError({'kind': ['Unknown document kind.']})


def check_extension(kind, filename):
    """A kind takes only the file types on its accept list; an unknown type is refused for any kind."""
    extension = kinds.extension(filename)
    if extension not in kinds.ALLOWED_EXTENSIONS:
        raise ValidationError({'file': ["That file type isn't accepted."]})
    if kind and not kinds.accepts(kind, filename):
        accepted = ', '.join(kinds.BY_KEY[kind]['accept'])
        raise ValidationError({'file': [f'A {kinds.label(kind)} file must be one of: {accepted}.']})


def check_upload(upload, kind=None):
    """Size, type and first bytes. With `kind`, the type must also be one the kind accepts (and the kind known)."""
    if kind is not None:
        check_kind(kind)
    if upload.size > settings.FILE_UPLOAD_MAX_BYTES:
        raise FileTooLarge()
    check_extension(kind, upload.name)
    if not upload.size:
        raise ValidationError({'file': ['That file is empty.']})
    if not matches_extension(upload.name, read_head(upload)):
        extension = kinds.extension(upload.name)
        raise ValidationError({'file': [f"That file's contents are not a {extension} file."]})
