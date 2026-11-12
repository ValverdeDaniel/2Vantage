"""`review.rules.asks` (plan.md §6.12's asks shape; L55, L59): the shape a request stores, its refusals by field, and
the words its card shows."""

import pytest

from review.rules import ask_words, asks


def test_L55_a_clean_ask_keeps_the_stored_shape():
    cleaned, errors = asks.clean(
        {
            'intake': {'scope': 'missing', 'blocks': ['contacts', 'contacts']},
            'census': {'scope': 'missing', 'columns': ['dob'], 'file': True},
            'documents': {'slots': ['invoice@medical', 'claims'], 'missing': True},
            'questionnaires': [{'form': 'fl_blue_51'}],
        }
    )
    assert errors == {}
    assert cleaned == {
        'intake': {'scope': 'missing', 'keys': [], 'blocks': ['contacts']},
        'census': {'scope': 'missing', 'columns': ['dob'], 'cells': [], 'file': True},
        'questionnaires': [{'form': 'fl_blue_51', 'mode': 'online', 'picks': {'fields': [], 'blocks': []}}],
        'documents': {'slots': ['invoice@medical', 'claims'], 'missing': True},
    }


def test_L55_nothing_asked_is_refused():
    assert asks.clean({})[1] == {'asks': [asks.NOTHING]}
    assert asks.clean({'census': {'scope': 'none'}, 'documents': {'slots': []}})[1] == {'asks': [asks.NOTHING]}
    assert asks.clean('everything')[1] == {'asks': ['Send the asks as an object.']}


@pytest.mark.parametrize(
    ('raw', 'field'),
    [
        ({'intake': {'scope': 'most'}}, 'intake.scope'),
        ({'intake': {'scope': 'selected', 'keys': ['no_such_question']}}, 'intake.keys'),
        ({'intake': {'scope': 'selected'}}, 'intake.keys'),
        ({'intake': {'blocks': ['payroll']}}, 'intake.blocks'),
        ({'census': {'scope': 'some'}}, 'census.scope'),
        ({'census': {'scope': 'all', 'columns': ['shoe_size']}}, 'census.columns'),
        ({'census': {'scope': 'selected', 'cells': [['x', 'dob']]}}, 'census.cells'),
        ({'census': {'scope': 'selected', 'cells': [[1, 'shoe_size']]}}, 'census.cells'),
        ({'census': {'scope': 'selected', 'cells': [[n, 'dob'] for n in range(501)]}}, 'census.cells'),
        ({'questionnaires': [{'form': 'no_such_form'}]}, 'questionnaires'),
        ({'questionnaires': [{'form': 'fl_blue_51', 'mode': 'fax'}]}, 'questionnaires'),
        ({'documents': {'slots': ['sbc']}}, 'documents.slots'),  # a client is never asked for an SBC
        ({'documents': {'slots': ['claims@medical']}}, 'documents.slots'),  # only renewals and invoices name a line
        ({'documents': {'slots': ['invoice@pets']}}, 'documents.slots'),
    ],
)
def test_L55_each_refusal_names_its_field(raw, field):
    _cleaned, errors = asks.clean(raw)
    assert field in errors


def test_L8_a_request_card_names_what_it_asks():
    cleaned, _ = asks.clean(
        {
            'census': {'scope': 'missing', 'file': True},
            'intake': {'scope': 'selected', 'keys': ['sic_code'], 'blocks': ['bor']},
            'questionnaires': [{'form': 'stop_loss_siia', 'mode': 'upload'}],
            'documents': {'slots': ['invoice@medical'], 'missing': True},
        }
    )
    words = ask_words.words(cleaned)
    assert words[:4] == ['The census gaps', 'The census file', '1 intake question', 'Broker of record']
    assert words[4].endswith('(upload)')
    assert words[5:] == ['Current invoice · Medical', 'Any missing documents']
    assert ask_words.words({'census': {'scope': 'selected', 'cells': [[1, 'dob'], [2, 'dob']]}}) == ['2 census values']
    assert ask_words.words({'census': {'scope': 'all', 'columns': ['dob']}}) == ['1 census column']


def test_D203_the_sections_a_request_carries():
    assert asks.sections({'census': {'scope': 'none', 'file': True}}) == ['census']
    assert asks.sections({'documents': {'slots': [], 'missing': True}}) == ['intake']
    assert asks.sections({'intake': {'scope': 'all'}, 'questionnaires': [{'form': 'x'}]}) == ['intake', 'questionnaire']
