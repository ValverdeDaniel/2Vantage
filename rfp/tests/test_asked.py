"""Who the RFP asked, by line (plan.md §6.10; K117, J63; Q.9 row 26 "`asked_by_line` with no sends")."""

import pytest

from rfp.models import RfpRequest
from rfp.selectors import asked_by_line

pytestmark = pytest.mark.django_db


def test_K117_a_deal_with_no_rfp_sent_asked_nobody_and_reading_makes_no_row(deal):
    assert asked_by_line(deal) == {}
    assert not RfpRequest.objects.filter(deal=deal).exists()
    RfpRequest.objects.create(deal=deal, carriers=['cigna'])  # picked, never sent
    assert asked_by_line(deal) == {}


def test_K117_each_carrier_once_per_line_the_first_send_winning(deal):
    sends = {
        'draft-b': {
            'on': '2026-10-08',
            'at': '2026-10-08T15:00:00+00:00',
            'route': 'direct',
            'asked': [{'key': 'cigna', 'name': 'Cigna', 'lines': ['medical', 'dental']}],
        },
        'draft-a': {
            'on': '2026-10-01',
            'at': '2026-10-01T15:00:00+00:00',
            'route': 'warner',
            'asked': [
                {'key': None, 'name': 'VSP Vision Care', 'lines': ['vision']},
                {'key': 'cigna', 'name': 'Cigna', 'lines': ['medical']},
                {'key': None, 'name': 'Unknown carrier', 'lines': ['medical']},
            ],
        },
    }
    RfpRequest.objects.create(deal=deal, sends=sends)
    found = asked_by_line(deal)
    assert found['medical'] == [{'id': 'cigna', 'name': 'Cigna', 'on': '2026-10-01'}]
    assert found['dental'] == [{'id': 'cigna', 'name': 'Cigna', 'on': '2026-10-08'}]
    assert found['vision'][0]['id'].startswith('n:') and found['vision'][0]['name'] == 'VSP Vision Care'
