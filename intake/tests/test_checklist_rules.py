"""The marketing checklist's rules (plan.md §5.2; B25–B27; Q.9 row 40): tiers from the headcount and the band at 50
and 51 (OQ53), the items each deal owes, the line documents, and the waivers. Pure: facts in, rows out."""

import pytest

from intake import checklist

MEDICAL_SHOPPED = {
    'line': 'medical',
    'answered': True,
    'in_force': True,
    'this_year': 'market',
    'needs_documents': True,
    'documents': {},
}


def intent(rows=(MEDICAL_SHOPPED,), confirmed=False, stale=False):
    rows = [dict(row) for row in rows]
    return {
        'rows': rows,
        'confirmed': confirmed,
        'stale': stale,
        'counts': {
            'unanswered': sum(1 for row in rows if not row['answered']),
            'in_force': sum(1 for row in rows if row['in_force']),
        },
    }


def facts(**changes):
    base = {
        'headcount': 60,
        'census_ok': False,
        'intent': intent(),
        'requested_lines': ['medical'],
        'kinds': set(),
        'funding': set(),
        'self_funded': '',
        'forms': {},
        'stored': {},
    }
    return checklist.Facts(**{**base, **changes})


def by_key(found):
    return {row['key']: row for row in checklist.items(found)}


@pytest.mark.parametrize(
    ('count', 'tier'),
    [(None, 'micro'), (0, 'micro'), (10, 'micro'), (11, 'small'), (50, 'small'), (51, 'mid'), (99, 'mid'),
     (100, 'ge100')],
)  # fmt: skip
def test_B25_OQ53_the_tier_from_the_enrolled_headcount_with_the_band_at_50_and_51(count, tier):
    assert checklist.tier(count) == tier


def test_B25_the_census_asks_zip_codes_below_51_and_home_addresses_from_51():
    assert 'ZIP code' in by_key(facts(headcount=50))['census']['detail']
    assert 'home address' in by_key(facts(headcount=51))['census']['detail']
    card = checklist.card(facts(headcount=51), {'count': 51, 'source': 'advisor', 'estimate': False})
    assert (card['tier_label'], card['enrolled'], card['geo']) == ('51–99 enrolled', 51, 'home address')


def test_B26_the_questionnaires_words_follow_the_tier():
    assert by_key(facts(headcount=8))['medical_questionnaire']['label'].startswith('Individual medical questionnaires')
    assert by_key(facts(headcount=40))['medical_questionnaire']['label'].startswith('Group medical questionnaire')
    assert by_key(facts(headcount=60))['medical_questionnaire']['label'].startswith('Medical questionnaire')


def test_B26_salary_only_with_a_life_or_disability_line_and_the_questionnaire_only_when_medical_is_marketed():
    plain = by_key(facts())
    assert 'salary_occupation' not in plain and 'medical_questionnaire' in plain
    ancillary = by_key(facts(requested_lines=['dental', 'ltd']))
    assert 'salary_occupation' in ancillary and 'medical_questionnaire' not in ancillary
    assert 'medical_questionnaire' in by_key(facts(requested_lines=[]))  # nothing said yet: medical is armed


def test_B26_claims_at_100_or_level_or_self_funded_including_the_intake_answer():
    assert 'claims' not in by_key(facts(headcount=99))
    assert by_key(facts(headcount=100))['claims']['detail'].startswith('Last 2 years')
    assert 'claims' in by_key(facts(funding={'level_funded'}))
    assert 'claims' in by_key(facts(self_funded='Yes'))  # B26's fix: the old rule read coverage funding only
    assert 'claims' not in by_key(facts(self_funded='No', funding={'fully_insured'}))


def test_B26_the_two_derived_items_follow_the_coverage_confirmation_and_census_ok():
    rows = by_key(facts(intent=intent(confirmed=True), census_ok=True))
    assert rows['coverage_intent']['done'] and rows['census']['done']
    stale = by_key(facts(intent=intent(stale=True)))['coverage_intent']
    assert not stale['done'] and stale['detail'].startswith('Coverage or the shopping list changed')


def test_B26_a_document_item_is_done_by_its_file_an_on_file_tick_or_the_signed_form():
    assert by_key(facts(kinds={'questionnaire'}))['medical_questionnaire']['done']
    ticked = by_key(facts(stored={'medical_questionnaire': {'checked': True, 'by': 3, 'at': 'now'}}))
    assert ticked['medical_questionnaire']['done'] and ticked['medical_questionnaire']['attested']
    signed = by_key(facts(forms={'medical_questionnaire': {'form': 'fl_blue_51', 'source': 'tier', 'signed': True}}))
    assert signed['medical_questionnaire']['done'] and signed['medical_questionnaire']['form_key'] == 'fl_blue_51'
    assert not by_key(facts(kinds={'stop_loss'}))['medical_questionnaire']['done']  # a disclosure is not the form


def test_B26_each_line_in_force_and_shopped_holds_its_renewal_or_one_file_says_nothing_about_lines():
    dental = {**MEDICAL_SHOPPED, 'line': 'dental'}
    one_line = intent(rows=[{**MEDICAL_SHOPPED, 'documents': {'renewal': [1]}}, dental])
    assert not by_key(facts(intent=one_line, kinds={'renewal'}))['renewal']['done']
    both = intent(rows=[{**MEDICAL_SHOPPED, 'documents': {'renewal': [1]}}, {**dental, 'documents': {'renewal': [2]}}])
    assert by_key(facts(intent=both, kinds={'renewal'}))['renewal']['done']


def test_B26_renewal_and_invoice_read_not_needed_when_nothing_is_in_force_or_nothing_in_force_is_shopped():
    gap = {**MEDICAL_SHOPPED, 'in_force': False, 'needs_documents': False}
    nothing = by_key(facts(intent=intent(rows=[gap])))
    assert nothing['renewal']['auto_waived'] and nothing['renewal']['status'] == 'waived'
    assert nothing['invoice']['waived_reason'] == 'not_in_force'
    kept = {**MEDICAL_SHOPPED, 'this_year': 'keep', 'needs_documents': False}
    kept_rows = by_key(facts(intent=intent(rows=[kept])))
    assert kept_rows['renewal']['waived_reason'] == 'not_shopped'
    unanswered = {**MEDICAL_SHOPPED, 'answered': False, 'in_force': None, 'needs_documents': False}
    assert by_key(facts(intent=intent(rows=[unanswered])))['renewal']['status'] == 'missing'  # nobody said yet


def test_B27_waived_leaves_the_gate_and_still_needed_puts_a_satisfied_item_back():
    waived = by_key(facts(stored={'cobra': {'requirement': 'waived'}}))['cobra']
    assert (waived['status'], waived['waived']) == ('waived', True)
    forced = by_key(
        facts(kinds={'invoice'}, stored={'invoice': {'requirement': 'required', 'client_note': 'This year'}})
    )
    assert (forced['invoice']['status'], forced['invoice']['forced'], forced['invoice']['client_note']) == (
        'missing',
        True,
        'This year',
    )
    assert by_key(facts(stored={'census': {'requirement': 'waived'}}))['census']['status'] == 'missing'  # derived


def test_B26_the_stop_loss_disclosure_is_an_offer_until_a_form_is_picked_or_it_is_asked_for():
    offer = by_key(facts())['stop_loss_disclosure']
    assert (offer['optional'], offer['status']) == (True, 'offer')
    picked = by_key(facts(stored={'stop_loss_disclosure': {'form_key': 'siia'}}))['stop_loss_disclosure']
    assert (picked['optional'], picked['status'], picked['form_source']) == (False, 'missing', 'producer')
    forced = by_key(facts(stored={'stop_loss_disclosure': {'requirement': 'required'}}))['stop_loss_disclosure']
    assert not forced['optional']


def test_B27_the_meter_counts_what_the_gate_counts():
    rows = checklist.items(facts(stored={'cobra': {'requirement': 'waived'}}, census_ok=True))
    meter = checklist.meter(rows)
    counted = [r for r in rows if not r['waived'] and not r['optional']]
    assert meter == {
        'required': len(counted),
        'done': sum(1 for r in counted if r['done']),
        'missing': sum(1 for r in counted if not r['done']),
        'all_clear': all(r['done'] for r in counted),
    }
    assert 'cobra' not in {r['key'] for r in counted} and 'stop_loss_disclosure' not in {r['key'] for r in counted}


def test_B27_a_tick_keeps_who_and_when_and_the_requirement_keeps_the_tick():
    entry = checklist.ticked({}, True, 7, 'then')
    assert entry == {'checked': True, 'by': 7, 'at': 'then'}
    assert checklist.ticked(entry, True, 8, 'later') is None  # already ticked: nothing changes
    required = checklist.required_as(entry, 'required', 'Send this year’s')
    assert required == {**entry, 'requirement': 'required', 'client_note': 'Send this year’s'}
    assert checklist.required_as(required, '', 'ignored') == entry  # Undo clears the note with the requirement
    assert checklist.ticked(required, False, 7, 'now') == {'requirement': 'required', 'client_note': 'Send this year’s'}
