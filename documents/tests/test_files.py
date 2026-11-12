"""The File panel, Remove, Restore and the purge (plan.md §3.8, §7.4; E10–E16, E96; O.3.7; OQ23)."""

import os

import pytest

from conftest import make_deal, write_path_contract
from deals import activity
from deals.models import Activity
from deals.services import delete_client
from documents import services
from documents.models import Document

from .helpers import stored


def test_E10_patch_saves_the_details_and_records_them_without_the_label(api, user, deal):
    doc = stored(user, deal)
    response = api.patch(f'/api/documents/{doc.id}/', {'label': 'Example renewal', 'carrier': ' Aetna '}, format='json')
    assert response.status_code == 200
    assert response.json()['label'] == 'Example renewal' and response.json()['carrier'] == 'Aetna'
    row = Activity.objects.filter(deal=deal, action='updated').latest('id')
    assert row.document_id == doc.id
    assert {'t': f'document:{doc.id}', 'k': {'carrier': ['', 'Aetna']}} in row.changes
    assert {'t': f'document:{doc.id}', 'k': ['label']} in row.changes  # the key, never the text (§3.8)
    assert 'Example renewal' not in str(row.changes) + row.summary


def test_E14_an_unchanged_patch_writes_nothing(api, user, deal):
    doc = stored(user, deal, carrier='Aetna')
    before = Activity.objects.count()
    response = api.patch(f'/api/documents/{doc.id}/', {'carrier': 'Aetna', 'kind': 'quote'}, format='json')
    assert response.status_code == 200 and Activity.objects.count() == before


def test_E11_a_kind_the_file_does_not_fit_saves_nothing_not_even_the_rename(api, user, deal):
    doc = stored(user, deal, name='rates.pdf')
    response = api.patch(f'/api/documents/{doc.id}/', {'label': 'Renamed', 'kind': 'plan_template'}, format='json')
    assert response.status_code == 400
    doc.refresh_from_db()
    assert doc.label == '' and doc.kind == 'quote'
    assert api.patch(f'/api/documents/{doc.id}/', {'kind': ''}, format='json').status_code == 400  # E6


def test_E13_a_role_only_for_the_kinds_that_ask(api, user, deal):
    doc = stored(user, deal, role='current')
    assert api.patch(f'/api/documents/{doc.id}/', {'kind': 'invoice'}, format='json').json()['role'] == ''
    asked = api.patch(f'/api/documents/{doc.id}/', {'kind': 'tpa_proposal', 'role': 'alternates'}, format='json')
    assert asked.json()['role'] == 'alternates'


def test_E74_a_kind_change_passes_the_write_path_contract(user, deal):
    doc = stored(user, deal, kind='quote')
    write_path_contract(
        user,
        doc,
        lambda: services.update(user, doc.id, {'kind': 'renewal'}),
        lambda d: d.kind,
        lambda: services.update(user, doc.id, {'kind': 'sbc'}),
    )


def test_E15_remove_archives_the_file_and_the_lists_drop_it(api, user, deal):
    doc = stored(user, deal)
    response = api.post(f'/api/documents/{doc.id}/archive/')
    assert response.status_code == 200 and response.json()['archived_at']
    assert api.get(f'/api/deals/{deal.id}/documents/').json() == []
    assert [d['id'] for d in api.get(f'/api/deals/{deal.id}/documents/?archived=1').json()] == [doc.id]
    assert not deal.documents.exists() and Document.all_objects.filter(pk=doc.id).exists()
    assert os.path.exists(doc.file.path)  # the bytes stay
    assert api.get(f'/api/documents/{doc.id}/download/').status_code == 200  # a removed file still opens
    row = Activity.objects.filter(deal=deal, action='archived').latest('id')
    assert row.changes == [{'t': f'document:{doc.id}', 'k': {'archived': [False, True]}}]


def test_E16_restore_puts_a_removed_file_back(api, user, deal):
    doc = stored(user, deal)
    services.archive(user, doc.id)
    response = api.post(f'/api/documents/{doc.id}/restore/')
    assert response.status_code == 200 and response.json()['archived_at'] is None
    assert [d['id'] for d in api.get(f'/api/deals/{deal.id}/documents/').json()] == [doc.id]
    count = Activity.objects.count()
    assert api.post(f'/api/documents/{doc.id}/restore/').status_code == 200 and Activity.objects.count() == count


def test_E16_reverting_a_remove_restores_the_file_once(user, deal):
    doc = stored(user, deal)
    services.archive(user, doc.id)
    row = Activity.objects.filter(deal=deal, action='archived').latest('id')
    activity.revert(row.id, user)
    assert Document.objects.filter(pk=doc.id).exists()
    with pytest.raises(activity.Refused):
        activity.revert(row.id, user)


def test_O37_protected_files_refuse_remove_purge_and_a_new_kind(api, admin_api, user, deal):
    doc = services.store_bytes(user, deal, 'Proposal.pdf', b'%PDF-1.4', 'proposal', 'Issued', protected=True)
    refused = api.post(f'/api/documents/{doc.id}/archive/')
    assert refused.status_code == 409 and 'cannot be removed' in refused.json()['detail']
    assert admin_api.delete(f'/api/documents/{doc.id}/').status_code == 409
    assert api.patch(f'/api/documents/{doc.id}/', {'kind': 'other'}, format='json').status_code == 409
    assert api.patch(f'/api/documents/{doc.id}/', {'label': 'Issued 2027'}, format='json').status_code == 200


def test_OQ23_only_an_admin_purges(api, admin_api, user, deal):
    doc = stored(user, deal)
    assert api.delete(f'/api/documents/{doc.id}/').status_code == 403
    assert admin_api.delete(f'/api/documents/{doc.id}/').status_code == 204
    assert not Document.all_objects.filter(pk=doc.id).exists()
    assert Activity.objects.filter(deal=deal, action='deleted', document_id=doc.id).exists()


def test_E96_a_purge_removes_the_bytes_only_once_it_commits(user, admin_user, deal, django_capture_on_commit_callbacks):
    doc = stored(user, deal)
    path = doc.file.path
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        services.purge(admin_user, doc.id)
    assert os.path.exists(path)  # not yet committed
    for callback in callbacks:
        callback()
    assert not os.path.exists(path)


def test_E96_a_client_cascade_removes_every_file_after_commit(user, django_capture_on_commit_callbacks):
    deal = make_deal(user, name='Cascade Co.')
    live, removed = stored(user, deal), stored(user, deal, name='old.pdf')
    services.archive(user, removed.id)
    paths = [live.file.path, removed.file.path]
    with django_capture_on_commit_callbacks(execute=True):
        delete_client(user, deal.client_id)
    assert not any(os.path.exists(path) for path in paths)


def test_E96_bytes_stay_when_the_delete_rolls_back(user, deal, django_capture_on_commit_callbacks):
    from django.db import transaction

    doc = stored(user, deal)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with pytest.raises(RuntimeError), transaction.atomic():
            Document.all_objects.get(pk=doc.id).delete()
            raise RuntimeError('rolled back')
    assert callbacks == [] and os.path.exists(doc.file.path) and Document.objects.filter(pk=doc.id).exists()
