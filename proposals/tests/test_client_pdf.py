"""The client PDF of GD1 through its download (plan.md §13.8 row 29, "done when": GD1's Client PDF has the old
Presentation pages, type floors and "(continued)" pages; J122–J140, J142; Q.9 row 29: client canaries in PDF text,
firm pages print nothing until written)."""

import io

import pytest
from django.core.files.base import ContentFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from pypdf import PdfReader

from conftest import make_big_deal
from deals.models import Activity
from proposals.layout import tokens
from proposals.models import FirmPages, TeamMember
from proposals.story import build
from quotes import services as plans
from quotes.services import priced
from synthetic_files import png

pytestmark = pytest.mark.django_db


def _pdf(api, deal):
    response = api.get(f'/api/deals/{deal.id}/proposal/files/pdf/')
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'
    assert response['Content-Disposition'].startswith('attachment;')
    return PdfReader(io.BytesIO(b''.join(response.streaming_content)))


def _texts(reader):
    return [page.extract_text() for page in reader.pages]


def test_S29_J122_GD1_client_pdf_has_the_presentation_pages_in_the_old_order(api, gd1):
    reader = _pdf(api, gd1.deal)
    texts = _texts(reader)
    box = reader.pages[0].mediabox
    assert (float(box.width), float(box.height)) == tokens.DECK_SIZE
    order = [
        'Golden Manufacturing (synthetic)',
        'Our recommendation at a glance',
        'What you pay today and what we recommend',
        'Executive summary',
        'Medical — your options',
        'Medical — Replacing: Aetna Open Access HDHP 3300',
        'Medical — our recommendation',
        'Dental — our recommendation',
        'Vision — our recommendation',
        'Thank you',
        'Important information',
    ]
    found = [next(n for n, text in enumerate(texts) if title in text) for title in order]
    assert found == sorted(found)
    assert all('Draft for review, not for clients' in text for text in texts)  # OQ35
    assert 'Enrollment basis:' in ' '.join(texts)
    assert 'WE RECOMMEND' in ' '.join(texts) and 'Option 1' in ' '.join(texts)


def test_S29_J140_GD1_a_plan_set_wider_than_a_page_continues(api, gd1, user):
    plans.star(user, gd1.deal, [gd1.refs['CG2']], True)
    texts = _texts(_pdf(api, gd1.deal))
    assert any('Medical — Replacing: Aetna Open Access HDHP 3300 (continued)' in text for text in texts)


def test_S29_J140_GD1_type_floors_hold_on_every_page(gd1):
    for page in build.deck(gd1.deal)['pages']:
        if page['fit']:
            assert page['fit']['size'] >= tokens.TABLE_TYPE['floor']
        for item in page['frames']:
            if item['t'] == 'table':
                sizes = [
                    s['size'] for c in item['cells'] for p in c['text']['paragraphs'] for ln in p['lines'] for s in ln
                ]
                assert min(sizes) >= tokens.TABLE_TYPE['floor']


def test_Q3_S29_the_download_writes_only_its_downloaded_row(api, gd1):
    before = set(Activity.objects.filter(deal=gd1.deal).values_list('id', flat=True))
    _pdf(api, gd1.deal)
    added = Activity.objects.filter(deal=gd1.deal).exclude(id__in=before)
    assert [(row.action, row.summary, row.area) for row in added] == [
        ('downloaded', 'Downloaded the client PDF (draft)', 'proposal')
    ]


def test_Q9_S29_client_canaries_never_reach_the_pdf(api, gd1, user):
    current = gd1.refs['A']
    plans.update_plan(user, current, {'notes': 'Zqcanarynote', 'values': {'network': 'Zqclientnetwork'}})
    plans.update_plan(user, gd1.refs['CG1'], {'values': {'mental_health_outpatient': 'Zqcanarymental'}})
    plans.star(user, gd1.deal, [gd1.refs['CG2']], True, reason='Zqcanarystar')
    text = ' '.join(_texts(_pdf(api, gd1.deal)))
    assert 'Zqclientnetwork' in text  # a client field prints
    for canary in ('Zqcanarynote', 'Zqcanarymental', 'Zqcanarystar'):
        assert canary not in text


def test_J125_J155_firm_pages_print_once_written(api, gd1):
    texts = ' '.join(_texts(_pdf(api, gd1.deal)))
    assert 'About Vantage Risk Solutions' not in texts and 'Your team' not in texts
    FirmPages.objects.create(
        about_text='We place benefits for manufacturers, and we answer the phone.',
        about_stats=[{'value': '20+', 'label': 'Years of experience'}],
        service_calendar=[{'meeting': 'Kick-off', 'topics': ['Review last year'], 'when': 'January'}],
    )
    member = TeamMember(name='Rosa Example', title='Account manager', bio='Twenty years in benefits.')
    member.photo.save('photo.png', ContentFile(png()), save=True)
    TeamMember.objects.create(name='Off Default', on_by_default=False)
    texts = _texts(_pdf(api, gd1.deal))
    joined = ' '.join(texts)
    for words in (
        'Agenda',
        'About Vantage Risk Solutions',
        'Your team',
        'Rosa Example',
        'How we work together through the year',
        'Twenty years in benefits.',
    ):
        assert words in joined
    assert 'Off Default' not in joined


def test_Q3_4_S29_the_deck_reads_the_same_queries_at_ten_and_two_hundred_plans(user):
    small, big = make_big_deal(user, 10, name='Small (synthetic)'), make_big_deal(user, 200, name='Big (synthetic)')

    def count(deal):
        with CaptureQueriesContext(connection) as queries:
            build.deck(deal)
        return len(queries)

    assert count(small) == count(big)


def test_J42_J155_the_builder_ledger_reads_the_firm_pages(api, gd1):
    def ledger():
        rows = api.get(f'/api/deals/{gd1.deal.id}/proposal/').json()['ledger']
        return {row['key']: row['ready'] for row in rows}

    assert [ledger()[key] for key in ('about', 'team', 'calendar', 'bios')] == [False] * 4
    FirmPages.objects.create(about_text='Who we are.', service_calendar=[{'meeting': 'Kick-off', 'topics': []}])
    TeamMember.objects.create(name='Rosa Example', bio='Twenty years in benefits.')
    assert [ledger()[key] for key in ('about', 'team', 'calendar', 'bios')] == [True] * 4


def test_J127_J131_GD1_a_negotiated_renewal_prints_the_first_offer_then_the_set_and_what_we_negotiated(api, gd1, user):
    five_off = {'kind': 'concession', 'all': {'op': 'pct_off', 'value': 5}}
    renewals = [gd1.refs[ref] for ref in ('A2', 'B2', 'C2')]
    versions = priced.price(user, gd1.deal, renewals, five_off).plans
    plans.set_recommended(user, next(v.id for v in versions if v.derived_from_id == gd1.refs['C2']), True)
    texts = _texts(_pdf(api, gd1.deal))
    first = next(n for n, text in enumerate(texts) if 'Medical — the first renewal offer' in text)
    renewal = next(n for n, text in enumerate(texts) if 'Medical — negotiated renewal' in text)
    assert first < renewal
    assert 'TODAY' in texts[renewal] and 'RENEWAL' in texts[renewal]
    assert 'Total annual premium today' in texts[renewal] and '% change' in texts[renewal]
    assert any('Medical: what we negotiated' in text for text in texts)
