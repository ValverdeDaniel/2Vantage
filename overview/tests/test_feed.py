"""The Timeline's read, `GET deals/{id}/overview/feed/` (plan.md §8.6; M70, M71; Q.9 row 63 "feed rows"): newest first,
no downloads or views in the rows or the count, 25 a page, each row's detail resolved at read time (the file's name,
the note's first line, the person a link went to), none for a subject that is gone, and a client's rows said as the
client's. Synthetic only."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

import synthetic_files
from deals import activity
from deals.models import Activity
from deals.services import add_note, create_contact, delete_note
from documents import services as documents
from review import services as review_services

pytestmark = pytest.mark.django_db

PDF = synthetic_files.text_pdf(['Example Health renewal (synthetic)'])


def feed(api, deal, page=1):
    response = api.get(f'/api/deals/{deal.id}/overview/feed/', {'page': page})
    assert response.status_code == 200, response.content
    return response.json()


def test_M70_downloads_and_views_are_neither_listed_nor_counted(api, user, deal):
    file = documents.upload(user, deal, SimpleUploadedFile('Renewal (synthetic).pdf', PDF), {'kind': 'renewal'})
    before = feed(api, deal)
    activity.log_access(deal, user, 'downloaded', 'a file', file.id)
    activity.log_access(deal, user, 'viewed', 'a file', file.id)
    after = feed(api, deal)
    assert after['count'] == before['count']
    assert not {row['action'] for row in after['results']} & {'downloaded', 'viewed'}
    assert Activity.objects.filter(deal=deal, action='downloaded').exists()


def test_M71_a_files_row_carries_its_name_and_a_removed_file_none(api, user, deal):
    file = documents.upload(user, deal, SimpleUploadedFile('Renewal (synthetic).pdf', PDF), {'kind': 'renewal'})
    row = next(row for row in feed(api, deal)['results'] if row['document_id'] == file.id)
    assert row['detail'] == 'Renewal (synthetic).pdf'
    assert 'Renewal (synthetic).pdf' not in row['summary']  # stored summaries name no file (M.5 B10)
    documents.archive(user, file.id)
    rows = [row for row in feed(api, deal)['results'] if row['document_id'] == file.id]
    assert rows and all(row['detail'] == '' for row in rows)


def test_M71_a_notes_row_carries_its_first_line_until_the_note_is_deleted(api, user, deal):
    note = add_note(user, deal.id, body='Called Casey about the census.\nShe will send it Friday.', kind='call')
    first = feed(api, deal)['results'][0]
    assert (first['summary'], first['detail'], first['actor']) == (
        'Logged a call',
        'Called Casey about the census.',
        'Dana',
    )
    delete_note(user, note.id)
    rows = feed(api, deal)['results']
    assert rows[0]['action'] == 'removed' and all(row['detail'] == '' for row in rows[:2])


def test_M71_a_links_row_names_the_person_and_their_role(api, user, deal):
    hr = create_contact(user, deal.client_id, role='hr_admin', name='Casey HR (synthetic)', email='casey@example.com')
    made = review_services.create(
        user, deal.id, {'asks': {'census': {'file': True}}, 'people': [{'contact_id': hr.id}]}
    )
    review_services.mark_sent(user, made.links[0][0].id, copied=True)
    sent = next(row for row in feed(api, deal)['results'] if row['area'] == 'review' and row['action'] != 'created')
    assert sent['detail'] == 'Casey HR (synthetic) · HR Admin'


def test_M71_a_clients_rows_are_said_as_the_clients(api, user, deal):
    activity.record(deal, None, 'review', 'client_opened', 'Client opened their link', actor_kind='client')
    row = feed(api, deal)['results'][0]
    assert (row['actor_kind'], row['actor']) == ('client', 'The client')


def test_M70_show_more_pages_25_rows_newest_first(api, user, deal):
    for n in range(27):
        add_note(user, deal.id, body=f'Note {n} (synthetic)')
    first = feed(api, deal)
    assert len(first['results']) == 25 and first['next'] and first['count'] >= 27
    assert first['results'][0]['detail'] == 'Note 26 (synthetic)'
    second = feed(api, deal, page=2)
    assert len(second['results']) == first['count'] - 25


def test_Q3_4_a_feed_page_reads_its_details_in_the_same_queries_however_many_subjects(api, user):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from conftest import make_deal

    def queries(deal):
        with CaptureQueriesContext(connection) as found:
            assert api.get(f'/api/deals/{deal.id}/overview/feed/').status_code == 200
        return len(found.captured_queries)

    small, big = make_deal(user, name='Small (synthetic)'), make_deal(user, name='Big (synthetic)')
    for deal, count in ((small, 1), (big, 8)):
        for n in range(count):
            add_note(user, deal.id, body=f'Note {n} (synthetic)', kind='call')
            documents.upload(user, deal, SimpleUploadedFile(f'Renewal {n} (synthetic).pdf', PDF), {'kind': 'renewal'})
    assert queries(small) == queries(big)
