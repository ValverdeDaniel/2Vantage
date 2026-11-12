"""The SBC reader (plan.md §10.4, §13.7 row 22; Q.9 row 22 "SBC rules"; D15, D38, D47, OQ33): design values only,
never a new plan but an unticked design-only one, the SBC beating a quote's value (flagged) and never a typed one,
always waiting for review. Claude is the fake client; every file and figure is synthetic."""

import pytest

from ai import land
from ai import services as ai
from deals.models import Activity
from documents.review_rules import open_warning
from quotes.models import Plan
from quotes.reader import rules
from quotes.reader.sbc import UNMATCHED
from quotes.tests.sbc_world import add_sbc, quote_world, read_sbc

pytestmark = pytest.mark.django_db

DESIGN = {'pcp_copay': '35', 'deductible_single': '2500', 'specialist_copay': '60', 'rate_ee': '999.99'}


def items_by_plan(job):
    return {item['plan']: item for item in job.result['items']}


def test_F47_D15_OQ33_an_sbc_read_waits_for_review_even_for_an_admin_and_writes_nothing(admin_user, fake_claude):
    deal, _current, _renewal, cigna = quote_world(admin_user)
    document = add_sbc(admin_user, deal, fake_claude, 'Cigna', 'Open Access 2500', DESIGN)
    rows = Activity.objects.filter(deal=deal).count()
    before = Plan.objects.get(pk=cigna.id).values
    job = read_sbc(admin_user, deal, document)
    assert (job.land, job.wait_reason, job.resolution) == (land.STAGED, land.ALWAYS, '')
    assert Plan.objects.get(pk=cigna.id).values == before
    assert Activity.objects.filter(deal=deal).count() == rows


def test_D47_design_values_only_and_the_sbc_beats_a_quotes_value_flagged(admin_user, fake_claude):
    deal, _current, _renewal, cigna = quote_world(admin_user)
    document = add_sbc(admin_user, deal, fake_claude, 'Cigna', 'Open Access 2500', DESIGN)
    job = read_sbc(admin_user, deal, document)
    item = items_by_plan(job)[cigna.id]
    assert item['op'] == 'set_values'
    values = {value['key']: value for value in item['values']}
    assert 'rate_ee' not in values  # an SBC prints no rates: dropped whatever Claude returns
    assert 'deductible_single' not in values  # equal: nothing to write (D60)
    assert values['specialist_copay']['tick'] and not values['specialist_copay']['low']  # a blank filled
    assert values['pcp_copay']['tick'] and values['pcp_copay']['old'] == '30'
    assert '35' in values['pcp_copay']['low'] and '30' in values['pcp_copay']['low']  # flagged with both figures
    assert any('rate' in finding['text'] for finding in job.result['findings'])
    [conflict] = job.result['conflicts']  # the card's "Where the SBC and the quote disagree"
    assert (conflict['key'], conflict['quote'], conflict['sbc'], conflict['kept']) == ('pcp_copay', '30', '35', '')

    landed_job, landed = ai.apply(admin_user, job.id)
    plan = Plan.objects.get(pk=cigna.id)
    assert (plan.values['pcp_copay'], plan.values['specialist_copay'], plan.values['rate_ee']) == ('35', '60', '512.34')
    assert open_warning(plan.sources['pcp_copay']) and not open_warning(plan.sources['specialist_copay'])
    assert plan.flags >= 1
    assert plan.sources['pcp_copay']['doc'] == document.id

    ai.undo(admin_user, landed_job.id)
    plan = Plan.objects.get(pk=cigna.id)
    assert plan.values['pcp_copay'] == '30' and 'specialist_copay' not in plan.values
    assert landed['activity_ids']


def test_D47_D61_a_typed_value_beats_the_sbc_left_alone_and_said(admin_user, fake_claude):
    deal, current, renewal, _cigna = quote_world(admin_user)
    document = add_sbc(admin_user, deal, fake_claude, 'Seabreeze Health', 'Gold PPO 2000', {'pcp_copay': '40'})
    job = read_sbc(admin_user, deal, document)
    by_plan = items_by_plan(job)
    assert set(by_plan) == {current.id, renewal.id}  # a current plan and its renewal named alike both take it
    value = by_plan[current.id]['values'][0]
    assert (value['key'], value['tick'], value['why']) == ('pcp_copay', False, rules.LEFT_ALONE['typed'])
    assert any('Gold PPO 2000' in finding['text'] and '40' in finding['text'] for finding in job.result['findings'])
    ai.apply(admin_user, job.id)
    assert Plan.objects.get(pk=current.id).values['pcp_copay'] == '25'


def test_D38_attached_to_a_plan_the_sbc_goes_to_it_whatever_its_name(admin_user, fake_claude):
    deal, _current, _renewal, cigna = quote_world(admin_user)
    document = add_sbc(admin_user, deal, fake_claude, 'Cigna Healthcare', 'OAP Gold (SBC)', {'er_copay': '300'})
    job = read_sbc(admin_user, deal, document, plan=cigna.id)
    assert job.result['attached'] == cigna.id
    [item] = job.result['items']
    assert (item['plan'], item['op'], item['matched'], item['tick']) == (cigna.id, 'set_values', 'attached', True)
    assert item['sbc_name'] == 'Cigna Healthcare OAP Gold (SBC)'


def test_D47_an_sbc_that_matches_no_plan_is_an_unticked_design_only_plan(admin_user, fake_claude):
    deal, *_plans = quote_world(admin_user)
    count = Plan.objects.filter(deal=deal).count()
    document = add_sbc(admin_user, deal, fake_claude, 'Pinecrest Health', 'Silver 4000', DESIGN)
    job = read_sbc(admin_user, deal, document)
    [item] = job.result['items']
    assert (item['op'], item['role'], item['tick'], item['why']) == ('create_plan', 'alternate', False, UNMATCHED)
    assert {value['key'] for value in item['values']} == {'pcp_copay', 'deductible_single', 'specialist_copay'}
    ai.apply(admin_user, job.id)  # "Use this scan" leaves it out: never a new plan unless the person ticks it
    assert Plan.objects.filter(deal=deal).count() == count


def test_D47_a_quote_read_leaves_an_sbc_value_alone(admin_user, fake_claude):
    from quotes.reader import changes

    deal, _current, _renewal, cigna = quote_world(admin_user)
    document = add_sbc(admin_user, deal, fake_claude, 'Cigna', 'Open Access 2500', {'pcp_copay': '35'})
    ai.apply(admin_user, read_sbc(admin_user, deal, document).id)
    plan = Plan.objects.get(pk=cigna.id)
    entry = {'value': '30', 'doc': None, 'page': 2, 'cell': '', 'unsure': False, 'label': 'PCP'}
    staged, _problem = rules.staged_value(
        'pcp_copay',
        entry,
        old_value=plan.values['pcp_copay'],
        old_source=plan.sources['pcp_copay'],
        sbc_docs=changes.sbc_documents(deal),
    )
    assert (staged['tick'], staged['why']) == (False, rules.LEFT_ALONE['sbc'])
