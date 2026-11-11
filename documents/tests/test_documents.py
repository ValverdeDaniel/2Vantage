"""Documents, version 1 (plan.md §3.8, §7.4, §12.3)."""

import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from deals.models import Activity
from documents.models import Document


def upload(api, deal, name='quote.pdf', content=b'%PDF-1.4 test', **meta):
    return api.post(
        f'/api/deals/{deal.id}/documents/', {'file': SimpleUploadedFile(name, content), **meta}, format='multipart'
    )


def test_upload_list_edit_delete(api, deal):
    created = upload(api, deal, kind='quote', role='alternates', carrier='Cigna', lines='["medical"]')
    assert created.status_code == 201
    doc = created.json()
    assert doc['kind'] == 'quote' and doc['role'] == 'alternates' and doc['lines'] == ['medical']
    assert [d['id'] for d in api.get(f'/api/deals/{deal.id}/documents/').json()] == [doc['id']]
    edited = api.patch(f'/api/documents/{doc["id"]}/', {'label': 'Cigna quote', 'kind': 'invoice'}, format='json')
    assert edited.json()['label'] == 'Cigna quote' and edited.json()['role'] == ''  # role only for quotes etc.
    path = Document.objects.get(pk=doc['id']).file.path
    assert os.path.exists(path)
    assert api.delete(f'/api/documents/{doc["id"]}/').status_code == 204
    assert not os.path.exists(path)


def test_download_requires_sign_in_and_sets_headers(api, anon_api, deal):
    doc = upload(api, deal).json()
    assert anon_api.get(f'/api/documents/{doc["id"]}/download/').status_code in (401, 403)
    response = api.get(f'/api/documents/{doc["id"]}/download/')
    assert response.status_code == 200
    assert response['X-Content-Type-Options'] == 'nosniff'
    assert response['Cache-Control'] == 'private, no-store'
    assert response['Content-Type'] == 'application/pdf'
    assert 'attachment' in response['Content-Disposition']
    assert response.get('Content-Encoding') is None


def test_extension_and_size_limits(api, deal):
    assert upload(api, deal, name='run.exe').status_code == 400
    with override_settings(FILE_UPLOAD_MAX_BYTES=10):
        assert upload(api, deal, content=b'x' * 11).status_code == 413


def test_phi_downloads_are_recorded_without_the_file_name(api, deal):
    doc = upload(api, deal, name='Jane Doe census.xlsx', content=b'x', kind='census').json()
    api.get(f'/api/documents/{doc["id"]}/download/')
    rows = Activity.objects.filter(deal=deal, action='downloaded')
    assert rows.count() == 1
    assert all('Jane' not in row.summary for row in Activity.objects.filter(deal=deal))
