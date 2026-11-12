"""Uploads (plan.md §3.8, §6.3, §7.4; E6, E7, D52; OQ24): the one door, its checks, and what it stores."""

import os
import re

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

import synthetic_files
from deals import activity
from deals.models import Activity
from documents import services
from documents.models import Document

from .helpers import RATES_PDF, RATES_XLSX_ROWS, ROSTER_PDF, stored, upload, xlsx


def test_E6_upload_stores_the_file_with_its_details(api, deal):
    created = upload(api, deal, kind='quote', role='alternates', carrier='Cigna', lines='["dental", "medical"]')
    assert created.status_code == 201
    doc = created.json()
    assert doc['kind'] == 'quote' and doc['bucket'] == 'proposal' and doc['role'] == 'alternates'
    assert doc['lines'] == ['medical', 'dental']  # the deal's line order
    assert doc['shape'] == 'pdf' and doc['page_count'] == 2 and not doc['protected']
    assert [d['id'] for d in api.get(f'/api/deals/{deal.id}/documents/').json()] == [doc['id']]
    row = Activity.objects.get(deal=deal, action='created', area='documents')
    assert row.document_id == doc['id'] and 'quote.pdf' not in row.summary  # the kind, never the file's name


def test_E6_a_blank_or_unknown_kind_answers_400_and_stores_nothing(api, deal):
    assert upload(api, deal, kind='').status_code == 400
    assert upload(api, deal, kind='wrap_doc').status_code == 400  # OQ26: the close-out kinds wait
    assert not Document.all_objects.filter(deal=deal).exists()


def test_E6_each_kind_takes_only_its_file_types(api, deal):
    assert upload(api, deal, name='roster.csv', content=b'name,dob\n', kind='questionnaire').status_code == 400
    assert upload(api, deal, name='roster.csv', content=b'name,dob\n', kind='census').status_code == 201
    assert upload(api, deal, name='letter.docx', content=b'PK\x03\x04rest', kind='quote').status_code == 400
    assert upload(api, deal, name='letter.docx', content=b'PK\x03\x04rest', kind='bor').status_code == 201
    assert upload(api, deal, name='run.exe', content=b'MZ\x90\x00', kind='other').status_code == 400


def test_E7_first_bytes_must_match_the_extension(api, deal):
    refused = upload(api, deal, name='quote.pdf', content=b'MZ\x90\x00 not a pdf')
    assert refused.status_code == 400 and 'file' in refused.json()
    assert upload(api, deal, name='rates.xlsx', content=b'%PDF-1.4 renamed').status_code == 400
    assert upload(api, deal, name='scan.png', content=synthetic_files.png(), kind='questionnaire').status_code == 201
    assert upload(api, deal, name='notes.csv', content=b'a,b\x00c', kind='other').status_code == 400


def test_E7_OQ24_files_over_the_cap_answer_413(api, deal):
    with override_settings(FILE_UPLOAD_MAX_BYTES=100):
        response = upload(api, deal, content=RATES_PDF + b' ' * 200)
    assert response.status_code == 413 and 'MB' in response.json()['detail']
    assert not Document.all_objects.filter(deal=deal).exists()


def test_E7_one_file_per_request(api, deal):
    files = [SimpleUploadedFile('a.pdf', RATES_PDF), SimpleUploadedFile('b.pdf', RATES_PDF)]
    response = api.post(f'/api/deals/{deal.id}/documents/', {'file': files, 'kind': 'quote'}, format='multipart')
    assert response.status_code == 400


def test_E7_a_pdf_page_count_is_read_and_an_unreadable_pdf_is_kept_without_one(user, deal):
    assert stored(user, deal).page_count == 2
    broken = stored(user, deal, name='broken.pdf', content=b'%PDF-1.4 truncated')
    assert broken.page_count is None and os.path.exists(broken.file.path)
    assert stored(user, deal, name='rates.xlsx', content=xlsx(RATES_XLSX_ROWS)).page_count is None


def test_E7_bytes_are_removed_when_the_upload_fails(user, deal, monkeypatch):
    before = set(_stored_names(deal))

    def fail(*args, **kwargs):
        raise RuntimeError('activity is down')

    monkeypatch.setattr(activity, 'record', fail)
    with pytest.raises(RuntimeError):
        stored(user, deal)
    assert set(_stored_names(deal)) == before
    assert not Document.all_objects.filter(deal=deal).exists()


def _stored_names(deal):
    from django.conf import settings

    folder = os.path.join(settings.MEDIA_ROOT, 'deals', str(deal.id))
    return os.listdir(folder) if os.path.isdir(folder) else []


def test_E7_stored_names_keep_the_deal_folder_and_drop_unsafe_characters(user, deal):
    doc = stored(user, deal, name='Rates <final>; v2.pdf')
    assert re.fullmatch(rf'deals/{deal.id}/[0-9a-f]{{32}}-Rates_final_v2\.pdf', doc.file.name)
    assert doc.original_name == 'Rates <final>; v2.pdf'


def test_D52_the_member_data_screen_is_stored_at_upload(user, deal):
    rates = stored(user, deal)
    assert rates.screen == {'version': 2, 'left_out_pages': [], 'image_pages': [], 'lists_members': False}
    roster = stored(user, deal, name='packet.pdf', content=ROSTER_PDF, kind='renewal')
    assert roster.screen['left_out_pages'] == [2] and roster.screen['lists_members'] is True
    sheet = stored(user, deal, name='census.xlsx', kind='census', content=xlsx([['Employee Name', 'DOB', 'Age']]))
    assert sheet.screen['lists_members'] is True and sheet.screen['left_out_pages'] == []
    image = stored(user, deal, name='scan.png', content=synthetic_files.png(), kind='questionnaire')
    assert image.screen['image_pages'] == [1]


def test_D52_a_page_without_text_is_an_image_page(user, deal):
    blank = synthetic_files.pdf([[(72, 720, 'Example Health renewal summary, page one of two')], []])
    assert stored(user, deal, name='scan.pdf', content=blank).screen['image_pages'] == [2]


def test_E15_store_bytes_keeps_an_app_made_file_unscreened_and_can_protect_it(user, deal):
    doc = services.store_bytes(user, deal, 'Proposal.pdf', RATES_PDF, 'proposal', 'Issued proposal', protected=True)
    assert doc.protected and doc.screen == {} and doc.page_count == 2
