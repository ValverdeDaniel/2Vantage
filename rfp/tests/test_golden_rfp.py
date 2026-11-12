"""Q.9 row 46 on GD6 (plan.md §12.6; Q.4 "GD6: band and route, printed counts, the packet's file list"): the packet's
contents, an `.eml` read back, the first send moving the deal to Quoting, and member data following the lines."""

import io

import pytest
from pypdf import PdfReader

from rfp import selectors
from rfp.models import RfpRequest

from .request import ask, attach, body, ctx, get, message, unzip

pytestmark = pytest.mark.django_db


def test_Q9_46_gd6_packet_eml_and_the_first_send(api, user, get_to_market):
    deal = get_to_market.step('contacts', 'census_arrives').built.deal
    ask(user, deal, 'florida_blue', 'unitedhealthcare', 'cigna', other_carriers='Oscar Health')
    claims = attach(user, deal, 'claims', 'Claims 2026 (synthetic).pdf', lines=['medical'])
    ask(user, deal, include={f'doc-{claims.id}': True})
    request = ctx(deal)
    assert (request.band, request.route) == ('large', 'direct')

    page = api.get(f'/api/deals/{deal.id}/rfp/').json()
    ticked = {row['key'] for row in page['packet']['rows'] if row['include']}
    assert {'cover', 'census-uhc', 'census-warner', 'questionnaire-fl_blue_51', f'doc-{claims.id}'} <= ticked
    assert not {'form', 'census-aetna', 'census-angle'} & ticked
    drafts = {draft['key']: draft for draft in page['drafts']['rows']}
    assert set(drafts) == {'florida_blue', 'unitedhealthcare', 'cigna', 'other'}
    assert 'questionnaire-fl_blue_51' in drafts['florida_blue']['attachment_keys']
    assert 'questionnaire-fl_blue_51' not in drafts['unitedhealthcare']['attachment_keys']
    assert 'census-uhc' in drafts['unitedhealthcare']['attachment_keys']
    assert f'doc-{claims.id}' not in drafts['other']['attachment_keys']  # OQ66

    files = unzip(body(get(api, deal, 'packet')))
    cover = PdfReader(io.BytesIO(files[next(name for name in files if name.endswith('RFP cover page.pdf'))]))
    assert f'{request.count}' in cover.pages[0].extract_text()  # the band's enrolled count prints (K17)

    mail = message(body(get(api, deal, 'draft-florida_blue')))
    assert mail['X-Unsent'] == '1' and mail['From'] is None
    names = [part.get_filename() for part in mail.iter_attachments()]
    assert any(name.endswith('.pdf') and 'questionnaire' in name for name in names)
    assert not any('Synthetic' in name for name in names)  # no member's name in any file name

    answer = api.post(f'/api/deals/{deal.id}/rfp/drafts/florida_blue/sent/', {'sent': True}, format='json').json()
    assert answer['stage'] == 'quoting'
    assert RfpRequest.objects.get(deal=deal).route == 'direct'
    assert [entry['name'] for entry in selectors.asked_by_line(deal)['medical']] == ['Florida Blue']
