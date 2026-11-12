"""`PATCH deals/{id}/proposal/` and `set_config` (plan.md §7.12; J19, J20, J.6.4, J.6.10; Q.3 #1, #8)."""

import threading

import pytest
from django.db import close_old_connections

from contract_helpers import later_clock, write_path_contract
from deals import activity
from deals.models import Activity
from proposals import config, services
from proposals.models import ProposalConfig

pytestmark = pytest.mark.django_db


def _patch(api, deal, body):
    return api.patch(f'/api/deals/{deal.id}/proposal/', body, format='json')


def test_J20_a_patch_returns_only_what_changed_and_a_get_reads_it(api, deal):
    response = _patch(api, deal, {'title': 'Benefits 2027', 'lines.medical.table_note': '* In network'})
    assert response.status_code == 200
    body = response.json()
    assert body['changed'] == {'title': 'Benefits 2027', 'lines.medical.table_note': '* In network'}
    assert body['cleared'] == [] and body['activity_id']
    config = api.get(f'/api/deals/{deal.id}/proposal/').json()['config']
    assert config == {'title': 'Benefits 2027', 'lines': {'medical': {'table_note': '* In network'}}}


def test_J20_an_unchanged_patch_writes_nothing_and_makes_no_row(api, deal):
    response = _patch(api, deal, {'title': ''})
    assert response.json() == {'changed': {}, 'cleared': [], 'activity_id': None}
    assert not ProposalConfig.objects.filter(deal=deal).exists()


@pytest.mark.parametrize(
    'body',
    [{'colour': 'red'}, {'lines.medical.parts.cost': 'no'}, {'reasons': 'why'}, {}, {'order': ['nowhere']}],
)
def test_J20_a_bad_patch_answers_400_with_a_sentence(api, deal, body):
    response = _patch(api, deal, body)
    assert response.status_code == 400
    assert all(isinstance(words, list) for words in response.json().values())


def test_Q3_1_J20_set_config_follows_the_write_path(user, deal):
    services.set_config(user, deal, {'intro': 'Hello'})  # the row exists before the contract watches it
    row = ProposalConfig.objects.get(deal=deal)
    write_path_contract(
        user,
        row,
        lambda: services.set_config(user, deal, {'title': 'Benefits 2027'}),
        lambda stored: stored.config.get('title'),
        lambda: services.set_config(user, deal, {'title': 'Benefits 2028'}),
    )


def test_J19_an_edit_clears_its_own_cards_mark_and_revert_puts_both_back(user, deal):
    services.set_mark(user, deal, 'rows', 'medical', True, ['medical', 'dental'])
    services.set_mark(user, deal, 'quotes', 'medical', True, ['medical', 'dental'])
    written = services.set_config(user, deal, {'lines.medical.rows': ['coinsurance']})
    assert written.cleared == ['marks.lines.medical.rows']
    stored = ProposalConfig.objects.get(deal=deal)
    assert 'rows' not in stored.marks['lines']['medical'] and 'quotes' in stored.marks['lines']['medical']
    activity.revert(written.activity.id, user)
    stored.refresh_from_db()
    assert config.get(stored.config, 'lines.medical.rows') is None  # every row with a value, as before
    assert stored.marks['lines']['medical']['rows']['by']


def test_J20_a_revert_is_refused_after_a_later_write_to_the_same_path(user, deal):
    first = services.set_config(user, deal, {'reasons.medical': 'Lower cost'})
    with later_clock():
        services.set_config(user, deal, {'reasons.medical': 'Same network'})
    with pytest.raises(activity.Refused) as refused:
        activity.revert(first.activity.id, user)
    assert 'The reasons for Medical' in refused.value.sentence


def test_J20_the_whole_reasons_map_spreads_into_its_paths(user, deal):
    written = services.set_config(user, deal, {'reasons': {'medical': 'A', 'dental': 'B'}})
    assert written.changed == {'reasons.medical': 'A', 'reasons.dental': 'B'}
    row = Activity.objects.get(pk=written.activity.id)
    assert row.area == 'proposal' and row.changes[0]['k']['reasons.dental'] == ['', 'B']


@pytest.mark.django_db(transaction=True)
def test_Q3_8_J20_two_writes_to_different_paths_both_survive(user, deal):
    barrier = threading.Barrier(2)
    errors = []

    def write(changes):
        try:
            barrier.wait(timeout=5)
            services.set_config(user, deal, changes)
        except Exception as exc:  # noqa: BLE001 (reported below)
            errors.append(exc)
        finally:
            close_old_connections()

    threads = [
        threading.Thread(target=write, args=({'title': 'Benefits 2027'},)),
        threading.Thread(target=write, args=({'lines.dental.table_note': '* PPO only'},)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    stored = ProposalConfig.objects.get(deal=deal).config
    assert stored['title'] == 'Benefits 2027' and stored['lines']['dental']['table_note'] == '* PPO only'
