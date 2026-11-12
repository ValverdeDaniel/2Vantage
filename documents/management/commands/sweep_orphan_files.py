"""manage.py sweep_orphan_files [--delete] — stored bytes no Document row points at (plan.md §6.3; E98).

An upload's bytes go when its own transaction fails, and a deleted row's once the deletion commits (E7, E96); a
rollback further out (a portal save that failed after its upload) can still leave bytes behind, and they may be member
data. This walks `deals/` in the storage and lists the files no row (archived ones included) names. A dry run by
default: it says how many and how large, never a name (a stored name keeps the uploaded file's name, which can carry a
person's, §3.8). `--delete` removes them.
"""

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from documents.models import Document, remove_bytes

ROOT = 'deals'


def stored_names(storage=default_storage, folder=ROOT):
    """Every file under `folder` in the storage, recursively, as storage names."""
    if not storage.exists(folder):
        return []
    folders, files = storage.listdir(folder)
    names = [f'{folder}/{name}' for name in files]
    for sub in folders:
        names.extend(stored_names(storage, f'{folder}/{sub}'))
    return names


def orphans(storage=default_storage):
    known = set(Document.all_objects.values_list('file', flat=True))
    return [name for name in stored_names(storage) if name not in known]


class Command(BaseCommand):
    help = 'List (or, with --delete, remove) stored files that no document row points at. Dry run by default.'

    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true', help='Remove the stray files (default: only count them)')

    def handle(self, *args, **options):
        strays = orphans()
        size = sum(default_storage.size(name) for name in strays)
        if options['delete']:
            for name in strays:
                remove_bytes(default_storage, name)
            self.stdout.write(f'Removed {len(strays)} stray file(s), {size} bytes.')
        else:
            self.stdout.write(f'{len(strays)} stray file(s), {size} bytes. Run with --delete to remove them.')
