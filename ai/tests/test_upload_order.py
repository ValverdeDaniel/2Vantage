"""A read takes its files in upload order (plan.md §10.4; D.6) and a later file wins a value two files disagree on
(D57): upload order is the order the files were stored, by id, never the clock's, which steps back under load."""

from datetime import timedelta

from ai import read_files
from documents.models import Document
from documents.tests.helpers import stored


def test_D57_the_later_upload_reads_last_even_when_the_clock_stepped_back(user, deal):
    older, newer = stored(user, deal, name='first.pdf'), stored(user, deal, name='second.pdf')
    # The clock stepped back a second between the two uploads (a VM resyncing its time under load).
    Document.all_objects.filter(pk=newer.pk).update(uploaded_at=older.uploaded_at - timedelta(seconds=1))
    files, failed = read_files.from_documents(list(Document.all_objects.filter(pk__in=[newer.pk, older.pk])))
    assert failed == [] and [(file.id, file.order) for file in files] == [(older.id, 0), (newer.id, 1)]
