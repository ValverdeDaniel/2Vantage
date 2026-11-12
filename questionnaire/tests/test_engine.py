"""The engine (G12–G25, G124, G125): pure, over the real specs."""

import pytest

from questionnaire import forms
from questionnaire.engine import narrow, walk
from questionnaire.engine.conditions import condition_met
from questionnaire.engine.options import active_effects, option_key, paired_value, resolve_options
from questionnaire.spec_payload import spec

FL = forms.FORMS['fl_blue_51']
SIIA = forms.FORMS['stop_loss_siia']
WP = forms.FORMS['wp_lg']


@pytest.mark.parametrize(
    'cond, values, met',
    [
        ({'field': 'q', 'op': 'nonempty'}, {'q': ' x '}, True),
        ({'field': 'q', 'op': 'nonempty'}, {'q': '  '}, False),
        ({'field': 'q', 'op': 'eq', 'value': 'Other'}, {'q': 'Other'}, True),
        ({'field': 'q', 'op': 'eq', 'value': 'Other'}, {}, False),
        ({'field': 'q', 'op': 'ne', 'value': 'No'}, {}, True),  # shown until No is picked
        ({'field': 'q', 'op': 'ne', 'value': 'No'}, {'q': 'No'}, False),
        ({'field': 'q', 'op': 'gt', 'value': 0}, {'q': '2'}, True),
        ({'field': 'q', 'op': 'gt', 'value': 0}, {'q': '0'}, False),
        ({'field': 'q', 'op': 'gte', 'value': 2}, {'q': '2'}, True),
        ({'field': 'q', 'op': 'gt', 'value': 0}, {'q': 'many'}, False),
        (None, {}, True),
    ],
)
def test_G14_every_operator_including_ne_on_a_blank(cond, values, met):
    assert condition_met(cond, values) is met


def test_G12_the_carriers_three_broken_labels_resolve_through_the_aliases():
    tumor = resolve_options(FL, 'conditions', {'drpMedCat': 'Non-cancerous Tumor'}, 'drpMedCondition')
    stomach = resolve_options(FL, 'conditions', {'drpMedCat': 'Stomach'}, 'drpMedCondition')
    brain = {'drpMedCat': 'Brain and/or Neurological', 'drpMedCondition': 'Unknown Brain/Neurological Condition'}
    assert tumor and stomach
    assert resolve_options(FL, 'conditions', brain, 'drpMedConDetail')
    assert option_key(FL, 'conditions', {'drpMedCat': 'Stomach'}, 'drpMedCondition').endswith('/Stomach/Esophagus')
    assert set(FL['aliases']['category'].values()) <= set(FL['tables']['conditions_by_category'])
    assert set(FL['aliases']['condition'].values()) <= set(FL['tables']['details_by_condition'])
    assert set(FL['aliases']['category']) <= set(FL['tables']['med_categories'])


def test_G12_an_empty_option_list_hides_the_dependent_picker():
    row = {'drpMedCat': 'Diabetes'}
    assert resolve_options(FL, 'conditions', row, 'drpMedCondition') == []
    assert 'drpMedCondition' not in walk.visible_fields(FL, 'conditions', row)


def test_G13_a_transplant_flag_survives_naming_a_transplant():
    assert active_effects(FL, 'conditions', {'drpMedCat': 'Transplants'})['transplant']
    named = {'drpMedCat': 'Transplants', 'drpMedCondition': 'Kidney Transplant'}
    assert active_effects(FL, 'conditions', named)['transplant']
    assert 'txtTransplantPlanned' in walk.visible_fields(FL, 'conditions', named)


def test_G13_a_condition_overrides_its_categorys_surgery_flag():
    category = {'drpMedCat': 'Non-cancerous Tumor'}
    assert active_effects(FL, 'conditions', category)['surgery']
    quiet = {**category, 'drpMedCondition': 'Benign Tumor of Bone'}
    assert not active_effects(FL, 'conditions', quiet)['surgery']
    loud = {**category, 'drpMedCondition': 'Benign Brain Tumor'}
    assert active_effects(FL, 'conditions', loud)['surgery']


def test_G13_a_fresh_row_shows_the_cancer_counts():
    assert active_effects(FL, 'conditions', {}) == {'cancer_counts': True}
    assert 'numCancerDetailyes' in walk.visible_fields(FL, 'conditions', {})


def test_G15_block_gates():
    from questionnaire.engine.conditions import block_visible

    assert block_visible(FL, 'plans', {}) and not block_visible(FL, 'plans', {'chkVirgin': 'No'})
    assert not block_visible(FL, 'conditions', {}) and block_visible(FL, 'conditions', {'chkMedCon': 'Yes'})
    assert block_visible(SIIA, 'risks', {}) and not block_visible(SIIA, 'risks', {'no_risks': 'Yes'})


def test_G16_the_sic_code_and_description_set_and_clear_each_other():
    assert paired_value(FL, '', 'drpSIC', '4213') == 'Trucking'
    assert paired_value(FL, '', 'drpSICDesc', 'Trucking') == '4213'
    assert paired_value(FL, '', 'drpSIC', '') == ''
    assert paired_value(FL, '', 'drpSIC', '0000') is None
    table = FL['tables']['sic_codes']
    duplicate = next(d for _c, d in table if sum(1 for _x, e in table if e == d) > 1)
    first = next(c for c, d in table if d == duplicate)
    assert paired_value(FL, '', 'drpSICDesc', duplicate) == first


def test_G17_the_carriers_test_rows_never_reach_the_pickers():
    codes = spec('fl_blue_51')['sections'][0]['fields']
    sic = next(f for f in codes if f['key'] == 'drpSICDesc')['options']
    assert sic and not any(text.startswith('Test Industry') for text in sic)
    assert sic == sorted(sic)


def test_G20_progress_counts_only_visible_required_answers_and_the_blanks_match():
    rows = {'plans': [(1, {})], 'conditions': [(2, {'drpMedCat': 'Diabetes'})]}
    view = ({'chkMedCon': 'No', 'chkVirgin': 'No'}, rows)
    found = walk.progress(FL, view)
    blanks = walk.blanks(FL, view)
    assert found['total'] - found['filled'] == len(blanks)
    assert not any(slot.startswith('conditions.') or slot.startswith('plans.') for slot in blanks)
    shown = ({'chkMedCon': 'Yes', 'chkVirgin': 'No'}, rows)
    assert 'conditions.2.numNumEEMedCon' in walk.blanks(FL, shown)
    assert walk.progress(FL, shown)['total'] == found['total'] + 2  # the row's category is answered, its count is not


def test_G19_hidden_answers_are_kept_but_never_exported():
    view = ({'chkVirgin': 'No', 'txtCurrentCarrier': 'Old Carrier'}, {'plans': [(1, {'txtCurrPlanName': 'PPO'})]})
    scalars, rows = walk.visible_values(FL, view)
    assert 'txtCurrentCarrier' not in scalars and rows['plans'] == []


def test_G21_the_comments_come_after_the_condition_grid():
    view = ({'chkMedCon': 'Yes'}, {'plans': [], 'conditions': [(5, {})]})
    order = [e['slot'] for e in walk.order(FL, view)]
    assert order.index('conditions.5.drpMedCat') < order.index('txtMcComments')


def test_G22_narrow_keeps_what_a_question_hangs_on_and_strips_the_signature_route():
    narrowed = narrow.narrow(FL, {'fields': ['txtRsnBidComments'], 'blocks': ['conditions']})
    keys = {f['key'] for s in narrowed['sections'] for f in s['fields']}
    assert {'txtRsnBidComments', 'txtRsnBid', 'chkMedCon'} <= keys
    assert set(narrowed['blocks']) == {'conditions'} and not narrowed['blank_pdf']
    assert narrow.narrow(FL, None) is FL


def test_G25_drivers_are_marked_in_the_spec():
    payload = spec('fl_blue_51')
    scalars = {f['key']: f for s in payload['sections'] for f in s['fields']}
    assert scalars['chkVirgin'].get('driver') and scalars['drpSIC'].get('driver') and scalars['txtRsnBid'].get('driver')
    assert not scalars['txtCoName'].get('driver')
    conditions = {f['key']: f for f in payload['blocks']['conditions']['fields']}
    assert conditions['drpMedCat'].get('driver') and conditions['drpMedCondition'].get('driver')


def test_G23_sensitive_slots_cover_the_medical_history_and_claimants():
    assert forms.is_sensitive('fl_blue_51', 'conditions', 'drpMedCat')
    assert forms.is_sensitive('fl_blue_51', '', 'chkMedCon') and not forms.is_sensitive('fl_blue_51', '', 'txtCoName')
    assert forms.is_sensitive('stop_loss_siia', 'risks', 'dob') and forms.is_sensitive('wp_lg', '', 'q5_ongoing_care')
    assert not forms.is_sensitive('wp_lg', 'current_rates', 'single')
    payload = spec('stop_loss_siia')
    assert all(f.get('sensitive') for f in payload['blocks']['risks']['fields'])


def test_G1_the_catalogue_lists_every_form_on_its_item():
    meta = forms.meta()
    assert {f['key'] for f in meta['forms']} == set(forms.FORMS)
    by_item = {item['key']: [o['key'] for o in item['options']] for item in meta['items']}
    assert by_item['medical_questionnaire'] == ['auto', 'fl_blue_51', 'wp_lg', 'upload']
    assert by_item['stop_loss_disclosure'] == ['', 'stop_loss_siia', 'upload']
    assert all(o['short'] for item in meta['items'] for o in item['options'])


def test_G5_OQ53_fifty_is_small_and_fifty_one_is_large():
    assert forms.band(50) == 'small' and forms.band(51) == 'large' and forms.band(None) == 'small'
    assert forms.band_default('medical_questionnaire', 60) == 'fl_blue_51'
    assert forms.band_default('medical_questionnaire', 40) == ''
    assert forms.band_default('stop_loss_disclosure', 400) == ''
