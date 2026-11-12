"""COBRA through intake (plan.md §5.3.7, §8.10; C25, O.6 #2; Q.9 row 41): the Census tab shows the checklist's COBRA
tick, read through intake's door; census never stores it."""

import pytest

from intake import services as intake

pytestmark = pytest.mark.django_db


def test_C25_the_census_page_reads_the_cobra_tick_from_intake(user, api, deal):
    page = lambda: api.get(f'/api/deals/{deal.id}/census/').json()  # noqa: E731
    assert page()['cobra'] == {
        'key': 'cobra',
        'label': 'COBRA participants',
        'checked': False,
        'by': None,
        'by_name': '',
        'at': None,
        'requirement': '',
    }
    intake.set_checklist_item(user, deal.id, 'cobra', checked=True)
    shown = page()['cobra']
    assert (shown['checked'], shown['by'], shown['by_name']) == (True, user.id, user.get_full_name() or user.username)


def test_C25_GD6_the_census_tab_reads_cobra_and_an_empty_roster(gd6, api):
    deal, _refs, _spec = gd6
    page = api.get(f'/api/deals/{deal.id}/census/').json()
    assert page['cobra']['checked'] is False and page['members'] == []
    assert page['summary']['employees'] == 0 and page['review'] == {'open': 0, 'check': 0, 'unflagged': 0}
