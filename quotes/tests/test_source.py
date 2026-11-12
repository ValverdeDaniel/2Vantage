"""↗ open in file (plan.md §7.8; E18, E31): one value's full source, read only (slice 15)."""

from django.core.files.uploadedfile import SimpleUploadedFile

import synthetic_files
from documents import services as documents
from quotes import services


def test_E18_a_value_source_names_its_file_cell_and_column_words(api, user, deal):
    pdf = synthetic_files.text_pdf(['Rates'], ['Employee only $512.34'])
    doc = documents.upload(user, deal, SimpleUploadedFile('renewal.pdf', pdf), {'kind': 'renewal'})
    plan = services.create_plan(
        user, deal, line='medical', role='current', carrier='Aetna', name='Gold PPO', values={'rate_ee': '512.34'},
        document=doc, cells={'rate_ee': 'Rates!B3'},
    )  # fmt: skip
    body = api.get(f'/api/plans/{plan.id}/source/', {'key': 'rate_ee'}).json()
    assert body['value'] == '512.34' and body['hint'] == 'Aetna Gold PPO'
    assert body['what'].endswith('· Aetna Gold PPO') and body['label'] in body['what']
    assert body['source']['doc'] == doc.id and body['source']['cell'] == 'Rates!B3'
    assert api.get(f'/api/plans/{plan.id}/source/', {'key': 'den_annual_max'}).status_code == 400
    assert api.get(f'/api/plans/{plan.id}/source/', {'key': 'deductible_single'}).json()['source'] is None


def test_E15_a_value_keeps_its_file_when_the_file_is_removed(api, user, deal):
    workbook = SimpleUploadedFile('rates.xlsx', b'PK synthetic')
    doc = documents.upload(user, deal, workbook, {'kind': 'quote'})
    plan = services.create_plan(
        user, deal, line='medical', role='current', carrier='Aetna', name='Gold PPO', values={'rate_ee': '512.34'},
        document=doc, cells={'rate_ee': 'Rates!B3'},
    )  # fmt: skip
    documents.archive(user, doc.id)
    plan.refresh_from_db()
    assert plan.sources['rate_ee']['doc'] == doc.id and plan.source_document_id == doc.id
    assert api.get(f'/api/plans/{plan.id}/source/', {'key': 'rate_ee'}).json()['source']['doc'] == doc.id
    board = api.get(f'/api/deals/{deal.id}/plans/', {'line': 'medical'}).json()
    assert {'id': doc.id, 'name': 'rates.xlsx'} in board['documents']  # a removed file keeps its name on the board
