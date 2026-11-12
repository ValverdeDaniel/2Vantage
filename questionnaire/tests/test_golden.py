"""Slice 42's done-when on the golden deals (Q.9 row 42): on GD6 Florida Blue 51+ is chosen by the band, with one
plans row per current plan, and the officer's signature locks the form; GD3 (quote-first, Q.3 #5) gets its band from
typed counts at checkpoint A, and the census at B never swaps the started form: it shows the notice (G133)."""

import pytest

from deals.models import Activity
from intake.selectors import intake_payload
from questionnaire import services
from questionnaire.models import Questionnaire
from questionnaire.selectors import payload

pytestmark = pytest.mark.django_db
FL = 'fl_blue_51'


def current_names(spec):
    return [p['name'] for p in spec['plans'] if p['line'] == 'medical' and p['role'] == 'current']


def test_G5_G134_GD6_florida_blue_is_chosen_by_the_band_with_a_plans_row_per_current_plan(gd6):
    found = payload.deal_forms(gd6.deal)
    assert [f['key'] for f in found['forms']] == [FL] and found['band'] == 'large'
    item = found['items']['medical_questionnaire']
    assert (item['form'], item['source'], item['notice']) == (FL, 'band', None)
    shown = payload.form_payload(gd6.deal, FL)
    names = [shown['values'].get(f'plans.{r["id"]}.txtCurrPlanName') for r in shown['rows']['plans']]
    assert names == current_names(gd6.spec) and not shown['started']
    assert shown['values']['txtCoName'] == gd6.spec['intake']['answers']['legal_name']


def test_G52_GD6_the_officers_signature_locks_the_form_and_completes_the_checklist_item(user, get_to_market):
    deal = get_to_market.step('contacts').built.deal
    shown = payload.form_payload(deal, FL)
    officer = get_to_market.built.spec['get_to_market']['contacts'][0]['name']
    assert shown['values']['txtgrprepname'] == officer  # the primary contact signs as the officer (G28)
    answers = {slot: 'No' for slot in ('chkFBPrior', 'chkMedCon')}
    services.set_answers(user, deal.id, FL, {**answers, 'txtRsnBid': 'Renewal Increase'})
    assert payload.form_payload(deal, FL)['blanks'] == []
    services.sign(user, deal.id, FL, 'officer', officer, authorized=True)
    row = Questionnaire.objects.get(deal=deal, form=FL)
    assert row.locked and row.answers['txtCoName'] == get_to_market.built.spec['intake']['answers']['legal_name']
    checklist = next(r for r in intake_payload(deal)['checklist']['items'] if r['key'] == 'medical_questionnaire')
    assert checklist['done'] and checklist['signed']
    assert Activity.objects.filter(deal=deal, area='questionnaire', action='signed').exists()


def test_G133_Q3_GD3_typed_counts_give_the_band_and_the_census_shows_the_notice(user, quote_first, golden_keys):
    key = golden_keys['GD3']
    deal = quote_first.built.deal
    assert payload.deal_forms(deal)['headcount']['count'] == key['checkpoints']['A']['headcount']['count']
    assert [f['key'] for f in payload.deal_forms(deal)['forms']] == [FL]
    services.set_answers(user, deal.id, FL, {'txtRsnBid': 'Renewal Increase'})
    quote_first.arrive('D').arrive('F').split().census()
    found = payload.deal_forms(deal)
    assert found['headcount']['count'] == key['checkpoints']['B']['headcount']['count'] and found['band'] == 'small'
    assert [f['key'] for f in found['forms']] == [FL]
    notice = found['items']['medical_questionnaire']['notice']
    assert notice['keep'] == FL and notice['text'] == 'Group size now says ≤50'
    shown = payload.form_payload(deal, FL)
    assert len(shown['rows']['plans']) == 1  # rows are kept from the first write; later plans add none


def test_G57_GD6_the_stamped_copy_prints_the_groups_facts_and_its_current_plan_in_their_boxes(gd6):
    from questionnaire.forms import fl_blue_51_layout as layout
    from questionnaire.pdf import build

    from .pdfs import inside

    data = build.build(gd6.deal, FL)  # a build writes nothing
    assert inside(data, layout.FIELD_BOXES['txtCoName'], gd6.spec['intake']['answers']['legal_name'])
    assert inside(data, layout.BLOCK_BOXES['plans']['txtCurrPlanName'], current_names(gd6.spec)[0])
