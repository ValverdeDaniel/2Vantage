"""The request's rules, pure (plan.md §5.7; K18, K20–K24, K29, K105): band, route, funding, eligibility, commission."""

import pytest

from deals import carriers as identities
from rfp import carriers, cleaners, request


@pytest.mark.parametrize(
    ('count', 'band'), [(50, 'small'), (51, 'large'), (0, 'small'), (None, 'small'), (120, 'large'), (2, 'small')]
)
def test_K18_OQ53_51_or_more_enrolled_is_large_and_50_is_small(count, band):
    assert request.band(count) == band


@pytest.mark.parametrize(
    ('stored', 'band', 'route', 'default'),
    [
        ('', 'small', 'warner', 'warner'),
        ('', 'large', 'direct', 'direct'),
        ('warner', 'large', 'warner', 'direct'),
        ('direct', 'small', 'direct', 'warner'),
        ('nonsense', 'large', 'direct', 'direct'),
    ],
)
def test_K20_the_route_follows_the_band_until_a_pick_overrides_it(stored, band, route, default):
    assert request.route(stored, band) == (route, default)


@pytest.mark.parametrize(
    ('incumbent', 'funding'),
    [
        ('fully_insured', ['fully_insured']),
        ('level_funded', ['level_funded']),
        ('self_funded', ['aso']),
        (None, ['fully_insured', 'level_funded']),
        ('', ['fully_insured', 'level_funded']),
    ],
)
def test_K22_the_default_funding_is_the_medical_incumbents_else_both(incumbent, funding):
    assert request.default_funding(incumbent) == funding


def test_K21_an_empty_funding_pick_is_kept_and_null_means_the_default():
    assert request.funding([], ['fully_insured']) == []
    assert request.funding(None, ['fully_insured']) == ['fully_insured']
    assert request.funding(['aso', 'fully_insured'], ['level_funded']) == ['fully_insured', 'aso']


def test_K24_a_carrier_off_the_form_at_the_band_says_which_form():
    eligible, reason, _lines = request.eligibility('curative', 'small', ['medical'])
    assert (eligible, reason) == (False, 'Not on the 2–50 form')
    assert request.eligibility('curative', 'large', ['medical'])[:2] == (True, '')


def test_K24_a_carrier_quoting_none_of_the_lines_says_so():
    assert request.eligibility('apl', 'small', ['medical', 'dental'])[:2] == (False, 'None of the lines you picked')
    eligible, _reason, overlap = request.eligibility('guardian', 'large', ['medical', 'dental', 'std', 'gap'])
    assert eligible and overlap == ['dental', 'std']


def test_K23_chips_keep_registry_order_and_mark_the_picks():
    rows = request.chips({'cigna', 'aetna'}, 'large', ['medical'], identities.CARRIERS)
    assert [row['key'] for row in rows] == list(identities.KEYS)
    assert [row['key'] for row in rows if row['selected']] == ['aetna', 'cigna']
    aetna = rows[0]
    assert (aetna['census_format'], aetna['line_labels'], aetna['group']) == ('aetna_gateway', ['Medical'], 'medical')
    trustmark = next(row for row in rows if row['key'] == 'trustmark')
    assert trustmark['on_form'] is False


def test_K105_rfp_carriers_are_the_carriers_deals_knows():
    assert list(carriers.ATTRIBUTES) == list(identities.KEYS)
    for key in carriers.ATTRIBUTES:
        for band in ('small', 'large'):
            assert all(column in carriers.COLUMN_LINES for column in carriers.columns_for(key, band))


def test_K23_the_warner_columns_cover_our_lines():
    assert carriers.lines_for('unitedhealthcare', 'small') == [
        'medical',
        'dental',
        'vision',
        'basic_life_add',
        'voluntary_life',
        'std',
        'ltd',
        'voluntary_std',
        'voluntary_ltd',
    ]
    assert carriers.lines_for('sidecar_health', 'small') == []


def test_K29_one_label_when_every_line_agrees():
    text, breakdown = request.commission_text(['medical', 'dental'], {}, {'type': 'pct', 'value': '5'})
    assert text == '5%'
    assert breakdown == ['Medical: 5%', 'Dental: 5%']


def test_K29_lines_grouped_by_label_larger_groups_first():
    rates = {'dental': {'type': 'pct', 'value': '15'}, 'vision': '15', 'basic_life_add': {'type': 'pepm', 'value': '2'}}
    text, _breakdown = request.commission_text(['medical', 'dental', 'vision', 'basic_life_add'], rates, '5')
    assert text == '15% Den/Vis · 5% Med · $2 PEPM Life'


def test_K29_no_rate_and_no_default_prints_nothing():
    assert request.commission_text(['medical'], {}, {}) == ('', [])
    assert request.commission_text(['medical'], {}, 'not a number') == ('', [])


def test_K25_carrier_clicks_add_and_remove_in_registry_order():
    current = dict(cleaners.EMPTY, carriers=['cigna'])
    wanted = cleaners.apply(current, {'carriers': {'add': ['aetna', 'unum'], 'remove': ['cigna']}}, list)
    assert wanted == {'carriers': ['aetna', 'unum']}


def test_K21_a_funding_click_on_the_default_starts_from_the_default():
    both = lambda: ['fully_insured', 'level_funded']  # noqa: E731
    assert cleaners.apply(dict(cleaners.EMPTY), {'funding': {'remove': ['level_funded']}}, both) == {
        'funding': ['fully_insured']
    }
    picked = dict(cleaners.EMPTY, funding=['aso'])
    assert cleaners.apply(picked, {'funding': {'remove': ['aso']}}, list) == {'funding': []}


@pytest.mark.parametrize(
    ('changes', 'field'),
    [
        ({'route': 'fax'}, 'route'),
        ({'carriers': ['aetna']}, 'carriers'),
        ({'carriers': {'add': ['no_such_carrier']}}, 'carriers'),
        ({'funding': {'add': ['cash']}}, 'funding'),
        ({'due_date': '13/45/2027'}, 'due_date'),
        ({'notes': 'x' * 2001}, 'notes'),
        ({'other_carriers': 'x' * 301}, 'other_carriers'),
        ({'notes': 7}, 'notes'),
        ({'lines': ['medical']}, 'lines'),
        ({'done': {}}, 'done'),
        ({'sends': {}}, 'sends'),
    ],
)
def test_K27_a_bad_value_is_refused_by_field(changes, field):
    with pytest.raises(cleaners.Invalid) as refused:
        cleaners.apply(dict(cleaners.EMPTY), changes, list)
    assert list(refused.value.errors) == [field]


def test_K26_text_is_trimmed_and_the_due_date_is_a_date():
    wanted = cleaners.apply(
        dict(cleaners.EMPTY), {'notes': '  Match the PPO.  ', 'due_date': '2027-01-15', 'other_carriers': None}, list
    )
    assert wanted == {'notes': 'Match the PPO.', 'due_date': '2027-01-15', 'other_carriers': ''}
    assert cleaners.apply(dict(cleaners.EMPTY), {'due_date': ''}, list) == {'due_date': None}


def test_K105_meta_serves_the_rfp_vocabularies_keyed_like_deals():
    from rfp import meta

    found = meta.meta()
    assert [entry['key'] for entry in found['carriers']] == list(identities.KEYS)
    assert [entry['key'] for entry in found['cards']] == ['coverage', 'request', 'checklist', 'packet', 'emails']
    assert [entry['key'] for entry in found['routes']] == ['warner', 'direct']
    assert [entry['key'] for entry in found['funding']] == list(request.FUNDING_KEYS)
