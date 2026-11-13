"""Q.3 #8 for the reads a client's upload starts (D44, L111; slice 59): two census files uploaded at once, each in its
own transaction, make one read of both — the second joins the first while it still waits to start, under the Deal's
lock — and neither upload fails."""

import threading
import time
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

from ai import kinds
from ai.models import Job
from ai.services import jobs
from documents.models import Document
from review.services import client_adds

from .portal_world import make_request

pytestmark = pytest.mark.django_db(transaction=True)

ROSTER = b'First Name,Last Name,Relationship,Date of Birth\r\nAvery,Example,Employee,03/04/1975\r\n'


def test_L111_Q3_8_two_census_files_at_once_make_one_read_of_both(settings, user, deal, fake_claude):
    settings.AI_JOBS_INLINE = False  # the worker's queue, as on the server
    link, _token, _pin = make_request(user, deal, {'census': {'file': True}})
    real = jobs.start

    def slow(*args, **kwargs):
        time.sleep(0.3)  # hold the Deal's lock while the job is made
        return real(*args, **kwargs)

    errors = []

    def upload(name):
        try:
            client_adds.upload(link.id, 'census_file', SimpleUploadedFile(name, ROSTER))
        except Exception as exc:  # noqa: BLE001 (reported below)
            errors.append(exc)
        finally:
            connection.close()

    with mock.patch.object(jobs, 'start', slow):
        threads = [threading.Thread(target=upload, args=(name,)) for name in ('one.csv', 'two.csv')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert errors == []
    files = sorted(Document.objects.filter(deal=deal, slot='census_file').values_list('id', flat=True))
    [job] = Job.objects.filter(deal=deal)
    assert job.status == kinds.QUEUED and sorted(job.documents) == files and len(files) == 2
