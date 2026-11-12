"""The packet zip, the email drafts and the `.eml` files, read back (plan.md §9.10, §9.11; K34–K63, K103, K104; OQ64,
OQ65, OQ66, OQ69). Outlook is not on the test machine: an `.eml` is proven by parsing it back as Outlook would read it
(its headers, `X-Unsent: 1`, no From, the attachments and their types)."""

import pytest

from deals.models import Activity
from rfp import audience, drafts
from rfp.cards import packet

from .request import ask, attach, body, ctx, get, message, unzip
from .roster import family

pytestmark = pytest.mark.django_db


def rows_by_key(request):
    return {row['key']: row for row in packet.rows(request)}


def test_K103_through_warner_the_zip_holds_the_ticked_files_a_summary_and_a_readme_naming_no_carrier(api, user, deal):
    family(user, deal)
    ask(user, deal, 'aetna', 'cigna', route='warner', notes='Please match the deductibles.')
    response = get(api, deal, 'packet')
    assert response.status_code == 200
    files = unzip(body(response))
    names = set(files)
    assert 'README.txt' in names and 'Quote request summary.txt' in names
    assert 'Example Co. - Quote request form.xlsx' in names
    assert {'Example Co. - Warner Pacific census.xlsx', 'Example Co. - Aetna census.xlsx'} <= names
    readme = files['README.txt'].decode('utf-8-sig')
    # It lists the files by name and says nothing of who is asked (Cigna has no file of its own).
    assert 'Cigna' not in readme and 'Carriers requested' not in readme and 'Please match the deductibles.' in readme
    assert 'Carriers requested: Aetna' in files['Quote request summary.txt'].decode('utf-8-sig')
    row = Activity.objects.filter(deal=deal, action='downloaded').latest('id')
    assert row.summary == 'Downloaded the RFP packet' and 'Avery' not in row.summary


def test_K49_OQ69_attachments_ride_under_documents_with_their_defaults(api, user, deal):
    ask(user, deal, 'aetna', route='direct')
    renewal = attach(user, deal, 'renewal', 'Renewal 2027 (synthetic).pdf')
    invoice = attach(user, deal, 'invoice', 'Invoice (synthetic).pdf')
    unset = attach(user, deal, 'sbc', 'SBC gold (synthetic).pdf')
    alternate = attach(user, deal, 'sbc', 'SBC other (synthetic).pdf', role='alternates')
    claims = attach(user, deal, 'claims', 'Jordan Reyes claims (synthetic).pdf')
    found = rows_by_key(ctx(deal))
    assert found[f'doc-{renewal.id}']['include']
    assert not found[f'doc-{invoice.id}']['include'] and found[f'doc-{invoice.id}']['deliberate']
    assert not found[f'doc-{unset.id}']['include'] and found[f'doc-{unset.id}']['reason'] == 'Role not set'
    assert found[f'doc-{alternate.id}']['deliberate'] == 'Another carrier’s plan'
    assert not found[f'doc-{claims.id}']['include']  # under 100 enrolled and nothing self-funded
    ask(user, deal, include={f'doc-{claims.id}': True})
    files = unzip(body(get(api, deal, 'packet')))
    assert 'Documents/Renewal 2027 (synthetic).pdf' in files
    assert 'Example Co. - RFP cover page.pdf' in files and 'Quote request summary.txt' not in files
    assert not any('Jordan' in name for name in files)  # a file carrying member data never keeps its name (rule 10)
    assert 'Documents/Example Co. - Claims experience.pdf' in files


def test_K55_nothing_ticked_is_400_and_a_file_that_cannot_be_built_is_409_by_its_label(api, user, deal):
    ask(user, deal, route='direct')
    renewal = attach(user, deal, 'renewal', 'Renewal (synthetic).pdf')
    keys = [row['key'] for row in packet.rows(ctx(deal)) if row['include']]
    ask(user, deal, include=dict.fromkeys(keys, False))
    assert get(api, deal, 'packet').status_code == 400
    ask(user, deal, include={f'doc-{renewal.id}': True})
    renewal.file.storage.delete(renewal.file.name)
    response = get(api, deal, 'packet')
    assert response.status_code == 409
    assert '“Renewal / rates”' in response.json()['detail']


def test_K56_a_tick_for_a_row_the_deal_does_not_have_is_400(api, user, deal):
    response = api.patch(f'/api/deals/{deal.id}/rfp/', {'include': {'doc-999999': True}}, format='json')
    assert response.status_code == 400


def test_K59_through_warner_one_draft_to_their_inbox_with_the_whole_packet(user, deal):
    ask(user, deal, 'aetna', route='warner')
    request = ctx(deal)
    found = drafts.drafts(request, packet.in_packet(packet.rows(request)))
    assert [draft['key'] for draft in found] == ['warner']
    warner = found[0]
    assert warner['to'] == 'FLQuoting@WarnerPacific.com'
    assert warner['subject'] == 'Quote request: Example Co. | Med, Den, Vis'
    assert 'Carriers requested: Aetna' in warner['body'] and warner['body'].startswith('Hi,\n\nPlease see the attached')


def test_K60_OQ65_direct_drafts_list_each_carriers_own_lines_and_name_no_other_carrier(user, deal):
    user.first_name, user.last_name, user.email = 'Dana', 'Broker', 'dana@example.test'
    user.save()
    ask(user, deal, 'aetna', 'guardian', route='direct', other_carriers='Oscar Health', due_date='2026-12-15')
    request = ctx(deal)
    found = {draft['key']: draft for draft in drafts.drafts(request, packet.in_packet(packet.rows(request)))}
    assert set(found) == {'aetna', 'guardian', 'other'}
    assert found['guardian']['subject'] == 'RFP: Example Co. | Den, Vis'
    assert found['aetna']['to'] == '' and found['aetna']['cc'] == 'dana@example.test'
    body_text = found['aetna']['body']
    assert 'Guardian' not in body_text and 'Oscar' not in body_text
    assert 'Quotes are due back by December 15, 2026.' in body_text
    assert 'Please reply all so your quote reaches dana@example.test.' in body_text
    assert body_text.endswith('Dana Broker\nVantage Risk Solutions')
    assert found['other']['label'] == 'Other carriers (Oscar Health)'


def test_K39_OQ66_each_carrier_gets_its_own_census_and_member_data_follows_the_lines(user, deal):
    family(user, deal)
    ask(user, deal, 'aetna', 'guardian', route='direct', other_carriers='Oscar Health')
    medical = attach(user, deal, 'claims', 'Claims medical (synthetic).pdf', lines=['medical'])
    unlined = attach(user, deal, 'claims', 'Claims (synthetic).pdf')
    ask(user, deal, include={f'doc-{medical.id}': True, f'doc-{unlined.id}': True})
    request = ctx(deal)
    found = {draft['key']: set(draft['attachment_keys']) for draft in drafts.drafts(request, packet.in_packet(
        packet.rows(request)))}  # fmt: skip
    assert 'census-aetna' in found['aetna'] and 'census-warner' not in found['aetna']
    assert 'census-warner' in found['guardian'] and 'census-warner' in found['other']
    assert f'doc-{medical.id}' in found['aetna'] and f'doc-{medical.id}' not in found['guardian']
    assert f'doc-{unlined.id}' in found['aetna'] and f'doc-{unlined.id}' not in found['guardian']
    assert not {f'doc-{medical.id}', f'doc-{unlined.id}'} & found['other']  # never "Other carriers"
    assert 'cover' in found['guardian'] and 'form' not in found['guardian']


def test_K104_asked_for_names_the_lines_and_keeps_unknown_names(user, deal):
    ask(user, deal, 'curative', 'aetna', other_carriers='UHC, Oscar Health')
    request = ctx(deal)
    asked = audience.asked_for(request, 'warner')
    by_name = {entry['name']: entry for entry in asked}
    assert by_name['Aetna']['lines'] == ['medical', 'dental', 'vision']
    assert by_name['Curative']['lines'] == ['medical']  # not on the 2–50 form, still named, so still asked
    assert by_name['UnitedHealthcare']['key'] == 'unitedhealthcare'
    assert by_name['Oscar Health'] == {'key': None, 'name': 'Oscar Health', 'lines': ['medical', 'dental', 'vision']}
    assert [entry['name'] for entry in audience.asked_for(request, 'aetna')] == ['Aetna']


def test_K63_the_eml_opens_as_an_unsent_draft_with_its_files(api, user, deal):
    family(user, deal)
    ask(user, deal, 'aetna', route='direct')
    response = get(api, deal, 'draft-aetna')
    assert response.status_code == 200
    assert response['Content-Type'] == 'message/rfc822'
    assert 'Example Co. - RFP email - Aetna.eml' in response['Content-Disposition']
    mail = message(body(response))
    assert mail['X-Unsent'] == '1' and mail['From'] is None
    assert mail['Subject'] == 'RFP: Example Co. | Med, Den, Vis' and mail['To'] is None
    assert 'Please see the attached RFP for Example Co.' in mail.get_body(('plain',)).get_content()
    files = {part.get_filename(): part.get_content_type() for part in mail.iter_attachments()}
    assert files['Example Co. - Aetna census.xlsx'] == (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    assert files['Example Co. - RFP cover page.pdf'] == 'application/pdf'
    assert 'Example Co. - Warner Pacific census.xlsx' not in files
    row = Activity.objects.filter(deal=deal, action='downloaded').latest('id')
    assert row.summary == 'Downloaded the Aetna email draft'
    assert get(api, deal, 'draft-cigna').status_code == 400
