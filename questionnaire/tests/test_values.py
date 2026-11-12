"""One answer per slot (G136), live prefill and `cleared` (G27, G33), the write whitelist (G16, G18) and prefill's
pure rules (G28, G134): no database."""

from datetime import date

from questionnaire import cleaning, forms, prefill, values
from questionnaire.values import Stored

FL = forms.FORMS['fl_blue_51']
WP = forms.FORMS['wp_lg']


def stored(**kw):
    base = {'answers': {}, 'sources': {}, 'client': {}, 'cleared': [], 'rows': {'plans': [{'id': 1}], 'conditions': []}}
    base.update(kw)
    return Stored(**base)


def test_G136_each_step_of_the_one_answer():
    live = {'txtCoName': 'Prefilled Co'}
    assert values.layer(stored(), live, 'txtCoName') == ('Prefilled Co', 'prefill')
    read = stored(answers={'txtCoName': 'Read Co'}, sources={'txtCoName': {'origin': 'ai'}})
    assert values.layer(read, live, 'txtCoName') == ('Read Co', 'stored')
    waiting = read._replace(client={'txtCoName': {'value': 'Client Co', 'status': 'pending'}})
    assert values.layer(waiting, live, 'txtCoName') == ('Client Co', 'client')
    typed = waiting._replace(answers={'txtCoName': 'Typed Co'}, sources={'txtCoName': {'origin': 'typed'}})
    assert values.layer(typed, live, 'txtCoName') == ('Typed Co', 'typed')
    reviewed = read._replace(client={'txtCoName': {'value': 'Client Co', 'status': 'rejected'}})
    assert values.layer(reviewed, live, 'txtCoName') == ('Read Co', 'stored')


def test_G89_a_confirm_entry_holds_the_value_it_confirms():
    confirm = stored(answers={'txtCoName': 'Read Co'}, client={'txtCoName': {'confirm': True, 'status': 'pending'}})
    assert values.layer(confirm, {}, 'txtCoName') == ('Read Co', 'client')


def test_G33_cleared_hides_only_the_live_prefill():
    live = {'txtCoName': 'Prefilled Co'}
    cleared = stored(cleared=['txtCoName'])
    assert values.effective(cleared, live, 'txtCoName') == ''
    waiting = cleared._replace(client={'txtCoName': {'value': 'Client Co', 'status': 'pending'}})
    assert values.effective(waiting, live, 'txtCoName') == 'Client Co'
    read = cleared._replace(answers={'txtCoName': 'Read Co'}, sources={'txtCoName': {'origin': 'ai'}})
    assert values.effective(read, live, 'txtCoName') == 'Read Co'


def test_G136_statuses_on_screen():
    s = stored(
        answers={'txtRsnBid': 'Other', 'chkFBPrior': 'No'},
        sources={'txtRsnBid': {'origin': 'typed'}, 'chkFBPrior': {'origin': 'ai', 'low': True}},
    )
    live = {'txtCoName': 'Prefilled Co'}
    view = values.shown(FL, s, live)
    found = values.statuses(FL, s, live, view)
    assert found['txtCoName'] == 'prefill' and found['chkFBPrior'] == 'to_check'
    assert found['dteAnnivDate'] == 'missing' and 'txtRsnBid' not in found
    assert 'txtRsnBidComments' not in found  # optional and blank: left out
    assert values.flags(FL, s, live) == 1


def view_of(s, live=None):
    return values.shown(FL, s, live or {})


def test_G18_every_drop_is_reported():
    s = stored()
    cleaned, dropped = cleaning.clean_batch(
        FL,
        view_of(s),
        s.rows,
        {
            'nope': 'x',
            'plans.9.txtCurrPlanName': 'PPO',
            'plans.1.numPlannum': '4',
            'numTAP': 'many',
            'txtRsnBid': 'Because',
            'State': ['FL'],
            'plans.1.txtCurrPlanName': 'PPO 1500',
            'not a slot!': 'x',
        },
    )
    reasons = {d['slot']: d['reason'] for d in dropped}
    assert reasons == {
        'nope': 'unknown',
        'plans.9.txtCurrPlanName': 'unknown_row',
        'plans.1.numPlannum': 'unknown',
        'numTAP': 'not_number',
        'txtRsnBid': 'not_offered',
        'State': 'unknown',
        'not a slot!': 'unknown',
    }
    assert next(d for d in dropped if d['slot'] == 'txtRsnBid')['options'][0] == 'Comparing Benefits & Rates'
    assert cleaned == {'plans.1.txtCurrPlanName': 'PPO 1500'}


def test_G18_a_dependent_answer_validates_against_its_parent_in_the_same_batch():
    s = stored(rows={'plans': [{'id': 1}], 'conditions': [{'id': 2}]}, answers={'chkMedCon': 'Yes'})
    batch = {'conditions.2.drpMedCondition': 'Kidney Transplant', 'conditions.2.drpMedCat': 'Transplants'}
    cleaned, dropped = cleaning.clean_batch(FL, view_of(s), s.rows, batch)
    assert not dropped and cleaned == batch
    _, dropped = cleaning.clean_batch(FL, view_of(s), s.rows, {'conditions.2.drpMedCondition': 'Kidney Transplant'})
    assert dropped[0]['reason'] == 'not_offered'


def test_G18_dates_yes_no_and_choices_are_normalised():
    s = stored()
    cleaned, _ = cleaning.clean_batch(
        FL, view_of(s), s.rows, {'dteAnnivDate': '4/1/2027', 'chkFBPrior': 'yes', 'State': 'fl', 'txtAdd2': '  Ste 2 '}
    )
    assert cleaned == {'dteAnnivDate': '2027-04-01', 'chkFBPrior': 'Yes', 'State': 'FL', 'txtAdd2': 'Ste 2'}
    assert cleaning.iso_day('3/14/80', today=date(2026, 11, 12)) == '1980-03-14'
    assert cleaning.iso_day('13/45/2020') == '13/45/2020'


def test_G16_a_picker_sets_its_twin_unless_the_batch_sets_both():
    s = stored()
    cleaned, _ = cleaning.clean_batch(FL, view_of(s), s.rows, {'drpSIC': '4213'})
    assert cleaned == {'drpSIC': '4213', 'drpSICDesc': 'Trucking'}
    cleaned, _ = cleaning.clean_batch(FL, view_of(s), s.rows, {'drpSIC': ''})
    assert cleaned == {'drpSIC': '', 'drpSICDesc': ''}


def group(**kw):
    base = {'group.legal_name': 'Example Co', 'group.sic': '', 'group.situs_state': ''}
    base.update(kw)
    return base


def test_G28_B7_no_FL_fallback_and_the_situs_state_fills_an_unparsed_address():
    assert prefill.facts(group())['address_state'] == ''
    assert prefill.facts(group(**{'group.situs_state': 'GA'}))['address_state'] == 'GA'


def test_G134_NAICS_leaves_the_sic_blank_and_a_leading_four_digit_code_fills_it():
    table = FL['tables']['sic_codes']
    assert prefill.sic_pair('484121', table) == ('', '')
    assert prefill.sic_pair('3441 — Fabricated Structural Metal', table)[0] == '3441'
    assert prefill.sic_pair('Trucking', table) == ('', '')


def test_G28_N1_no_carrier_means_no_replacing_answer():
    found = prefill.facts(group())
    assert found['current_carrier'] == '' and found['replacing_coverage'] == ''
    assert prefill.facts(group(**{'group.current_carrier': 'Florida Blue'}))['replacing_coverage'] == 'Yes'


def test_G134_one_starting_row_per_current_plan_and_warners_rates_copied():
    rows, last = prefill.starting_rows(FL, [11, 12])
    assert [r['plan'] for r in rows['plans']] == [11, 12] and rows['conditions'] == [] and last == 2
    rows, last = prefill.starting_rows(WP, [11, 12, 13, 14])
    assert [r.get('plan') for r in rows['current_rates']] == [11, 12, 13]  # up to the form's three options
    assert [r.get('plan') for r in rows['carriers']] == [None]
    plans = {
        11: {'name': 'PPO', 'rate_ee': '640.00', 'rate_es': '1380.00', 'rate_ec': '', 'rate_fam': '1910.00',
             'renewal': {'name': 'PPO renewal', 'rate_ee': '700.00'}},
    }  # fmt: skip
    found = prefill.values(WP, {'plans': plans}, prefill.starting_rows(WP, [11])[0])
    current = next(r['id'] for r in prefill.starting_rows(WP, [11])[0]['current_rates'])
    renewal = next(r['id'] for r in prefill.starting_rows(WP, [11])[0]['renewal_rates'])
    assert found[f'current_rates.{current}.single'] == '640.00'
    assert found[f'current_rates.{current}.double'] == '1380.00'
    assert f'current_rates.{current}.ee_child' not in found
    assert found[f'renewal_rates.{renewal}.plan_type'] == 'PPO renewal'


def test_G29_medical_answers_are_never_prefilled():
    prefilled = {f['key'] for s in FL['sections'] for f in s['fields'] if f.get('prefill')}
    assert not prefilled & {'chkMedCon', 'txtMcComments', 'drpEEContMethod', 'numERConPercent'}
    assert not any(f.get('prefill') for f in FL['blocks']['conditions']['fields'])
    assert not any(f.get('prefill') for f in FL['blocks']['plans']['fields'] if f['key'].startswith('num'))  # OQ56
