"""Every write to documents (plan.md §3.8, §6.3, §7.4; E.6). One door per action:

- `upload`, `store_bytes` (uploads.py): the only ways a Document is made.
- `update`, `archive`, `restore`, `purge` (changes.py): the File panel and Remove.
- `record_access`, `download_name` (access.py): who opened a file with member data, and its download name.
- `set_page_labels` (labels.py): a file's printed page numbers, from the quote reader's landing (E94).
- `check_upload` (documents/checks.py): the checks an upload passes, for doors that check before they read a file.
"""

from ..checks import check_upload
from .access import carries_members, download_name, record_access
from .changes import archive, purge, restore, update
from .labels import set_page_labels
from .uploads import store_bytes, upload

__all__ = [
    'archive',
    'carries_members',
    'check_upload',
    'download_name',
    'purge',
    'record_access',
    'restore',
    'set_page_labels',
    'store_bytes',
    'update',
    'upload',
]
