"""The Overview on the golden deals of Q.9 row 62 (GD3, GD6): quote-first states at checkpoint A, and a Get to Market
deal's facts read where intake holds them. Read-only: the module-scoped golden deals are never written."""

import pytest

from intake import selectors as intake_selectors
from quotes.summary import QUOTE_ROLES

pytestmark = pytest.mark.django_db


def overview(api, deal):
    response = api.get(f'/api/deals/{deal.id}/overview/')
    assert response.status_code == 200
    return response.json()


def test_Q9_62_GD3_quote_first_counts_its_quotes_and_asks_nothing_of_intake(api, gd3):
    """Checkpoint A: quotes priced from typed counts, no current plan, no intake answers. The header still answers:
    New business, a prospect who may be converted, every quote counted, and the medical incumbent open to typing (no
    current plan holds it). The Waiting banner, the stepper and Intake complete are the journey's (slice 61)."""
    payload = overview(api, gd3.deal)
    quotes = [plan for plan in gd3.spec['plans'] if plan['role'] in QUOTE_ROLES]
    assert payload['tiles']['plans_quoted'] == len(quotes)
    assert payload['identity']['type'] == 'new_business' and payload['identity']['legal_name'] == ''
    assert payload['client']['convert']['allowed'] is True
    assert payload['facts']['carrier']['editable'] is True and payload['facts']['carrier']['from'] is None


def test_Q9_62_GD6_reads_its_intake_answers_and_its_current_plans_carrier(api, gd6):
    payload = overview(api, gd6.deal)
    answers = intake_selectors.intake_payload(gd6.deal)['answers']
    assert payload['identity']['legal_name'] == answers['legal_name'] == gd6.spec['intake']['answers']['legal_name']
    for key in ('fein', 'sic_code', 'situs_state', 'employee_count'):
        assert payload['facts'][key] == str(answers.get(key) or ''), key
    current = [plan for plan in gd6.spec['plans'] if plan['role'] == 'current' and plan['line'] == 'medical']
    assert payload['facts']['carrier'] == {**payload['facts']['carrier'], 'from': 'plans', 'editable': False}
    assert payload['facts']['carrier']['value'] == current[0]['carrier']
