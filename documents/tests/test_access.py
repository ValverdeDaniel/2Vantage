"""Opening a file (plan.md §3.6, §3.8; E17, E99, K63, Q.8): the headers, and who opened a file with member data."""

from django.test import override_settings

from deals import downloads, selectors
from deals.models import Activity
from documents import screening

from .helpers import RATES_XLSX_ROWS, ROSTER_PDF, stored, xlsx


def _get(api, url):
    response = api.get(url)
    b''.join(response.streaming_content)
    return response


def test_E17_a_download_is_an_attachment_with_the_safe_headers(api, anon_api, user, deal):
    doc = stored(user, deal)
    assert anon_api.get(f'/api/documents/{doc.id}/download/').status_code == 401
    response = _get(api, f'/api/documents/{doc.id}/download/')
    assert response.status_code == 200 and response['Content-Type'] == 'application/pdf'
    assert response['Content-Disposition'].startswith('attachment') and 'quote.pdf' in response['Content-Disposition']
    assert response['X-Content-Type-Options'] == 'nosniff' and response['Cache-Control'] == 'private, no-store'
    assert response.get('Content-Encoding') is None and 'Content-Security-Policy' not in response


def test_E17_inline_opens_under_a_sandbox_csp(api, user, deal):
    doc = stored(user, deal)
    response = _get(api, f'/api/documents/{doc.id}/download/?inline=1')
    assert response['Content-Disposition'].startswith('inline')
    policy = response['Content-Security-Policy']
    assert 'sandbox' in policy and "default-src 'none'" in policy


def test_K63_content_types_come_from_the_extension_map():
    assert downloads.content_type_for('Packet.eml') == 'message/rfc822'
    assert downloads.content_type_for('Census.XLSX').endswith('spreadsheetml.sheet')
    assert downloads.content_type_for('files.zip') == 'application/zip'
    assert downloads.content_type_for('roster.csv') == 'text/csv'
    assert downloads.content_type_for('mystery.bin') == 'application/octet-stream'


def test_E99_a_phi_download_writes_one_row_with_the_id_and_never_the_name(api, user, deal):
    doc = stored(user, deal, name='Tester Alpha census.xlsx', kind='census', content=xlsx([['Plan'], ['Gold']]))
    last_updated = _last_updated(deal)
    response = _get(api, f'/api/documents/{doc.id}/download/')
    assert 'Tester' not in response['Content-Disposition']  # PHI files download as "<Client> - <Kind>" (Q.8)
    assert 'Example Co. - Census.xlsx' in response['Content-Disposition']
    rows = Activity.objects.filter(deal=deal, action='downloaded')
    assert [row.document_id for row in rows] == [doc.id]
    assert not any('Tester' in row.summary for row in Activity.objects.filter(deal=deal))
    assert _last_updated(deal) == last_updated
    assert all(row['action'] not in ('downloaded', 'viewed') for row in _feed(deal))


def _last_updated(deal):
    return selectors.client_rows().get(pk=deal.pk).last_activity_at


def _feed(deal):
    return [{'action': row.action} for row in selectors.activity_feed(deal)]


def test_E99_views_coalesce_per_file(api, user, deal):
    doc = stored(user, deal, name='claims.pdf', kind='claims')
    for _ in range(3):
        _get(api, f'/api/documents/{doc.id}/download/?inline=1')
    views = Activity.objects.filter(deal=deal, action='viewed')
    assert views.count() == 1 and views.get().count == 3 and views.get().document_id == doc.id


def test_E99_a_file_the_screen_found_people_in_is_logged_like_a_phi_kind(api, user, deal):
    packet = stored(user, deal, name='renewal.pdf', content=ROSTER_PDF, kind='renewal')
    assert screening.lists_members(packet)
    _get(api, f'/api/documents/{packet.id}/download/')
    assert Activity.objects.filter(deal=deal, action='downloaded', document_id=packet.id).exists()


def test_E99_OQ27_files_without_member_data_log_nothing(api, user, deal):
    for doc in (stored(user, deal), stored(user, deal, name='invoice.pdf', kind='invoice')):
        _get(api, f'/api/documents/{doc.id}/download/')
    assert not Activity.objects.filter(deal=deal, action__in=('downloaded', 'viewed')).exists()


def test_E99_a_sheet_window_of_a_census_is_a_view(api, user, deal):
    doc = stored(user, deal, name='census.xlsx', kind='census', content=xlsx(RATES_XLSX_ROWS))
    assert api.get(f'/api/documents/{doc.id}/sheet/').status_code == 200
    assert Activity.objects.filter(deal=deal, action='viewed', document_id=doc.id).exists()


def test_OQ22_reads_leave_flagged_pages_out_only_with_the_switch(user, deal):
    packet = stored(user, deal, name='renewal.pdf', content=ROSTER_PDF, kind='renewal')
    assert screening.pages_left_out(packet) == []  # off by default: files are read whole (D-225)
    with override_settings(AI_MEMBER_DATA_SCREEN=True):
        assert screening.pages_left_out(packet) == [2]


def test_E17_a_file_missing_from_storage_answers_404(api, user, deal):
    doc = stored(user, deal)
    doc.file.storage.delete(doc.file.name)
    assert api.get(f'/api/documents/{doc.id}/download/').status_code == 404
