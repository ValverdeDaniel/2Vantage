"""Booking at the sale (plan.md §5.6; H25–H32, H36, H120, H124; OQ75): what a sale books, what un-selling voids, and
what a rebook refreshes or keeps."""

import pytest

from commission import selectors, services
from commission.models import Record
from conftest import make_deal
from deals import activity
from deals.models import Activity
from intake.models import CurrentCoverage
from quotes import services as quotes

pytestmark = pytest.mark.django_db
TIERS = {'medical': {'EE': 10, 'ES': 3, 'EC': 2, 'FAM': 5}}


def plan(user, deal, carrier, name, line='medical', role='alternate', rate='500', **kw):
    values = {'rate_ee': rate, 'rate_es': rate, 'rate_ec': rate, 'rate_fam': rate} if rate else {}
    made = quotes.create_plan(user, deal, line=line, role=role, carrier=carrier, name=name, values=values, **kw)
    return made


@pytest.fixture
def sold_deal(user):
    """A deal with a current medical plan (10/3/2/5) and two Cigna and one UHC alternates, at 5 % agreed."""
    deal = make_deal(user, effective_date='2027-01-01')
    current = plan(user, deal, 'Aetna', 'Today', role='current')
    quotes.set_enrollment(user, deal, 'medical', plans=[{'id': current.id, 'enrollment': TIERS['medical']}])
    picks = {
        'c1': plan(user, deal, 'Cigna', 'One', replaces_ids=[current.id]),
        'c2': plan(user, deal, 'Cigna', 'Two', rate='400', replaces_ids=[current.id]),
        'u1': plan(user, deal, 'UnitedHealthcare', 'Three', rate='450', replaces_ids=[current.id]),
    }
    services.update(user, deal.id, {'rates': {'medical': '5'}})
    deal.picks = picks
    return deal


def sell(user, deal, *keys, sold=True):
    for key in keys:
        quotes.set_sold(user, deal.picks[key].id, sold)


def live(deal):
    return list(Record.objects.filter(deal=deal).exclude(status='void').order_by('carrier'))


def test_H25_a_sale_books_on_commit(user, sold_deal, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1')
    (record,) = live(sold_deal)
    assert (record.line, record.carrier, record.status) == ('medical', 'Cigna', 'booked')
    assert record.values['plan_ids'] == [sold_deal.picks['c1'].id]
    assert record.values['rate'] == {'type': 'pct', 'value': '5'}
    assert record.values['premium_annual'] == '120000.00'  # 500 × 20 a month × 12
    assert record.values['employees'] == 20
    assert record.sources['premium_annual']['origin'] == 'sale'
    assert record.year_number == 1 and not record.is_renewal
    row = Activity.objects.filter(deal=sold_deal, area='commission', action='booked').get()
    assert not row.revertible
    with pytest.raises(activity.Refused):
        activity.revert(row.id, user)


def test_H25_a_failing_receiver_leaves_the_sale_saved_and_the_tab_unbooked(
    user, api, sold_deal, monkeypatch, django_capture_on_commit_callbacks
):
    def broken(*args, **kwargs):
        raise RuntimeError('booking failed')

    monkeypatch.setattr('commission.services.booking.book_deal', broken)
    with django_capture_on_commit_callbacks(execute=True):
        answer = api.post(f'/api/plans/{sold_deal.picks["c1"].id}/sold/', {'sold': True}, format='json')
    assert answer.status_code == 200
    assert not Record.objects.filter(deal=sold_deal).exists()
    monkeypatch.undo()
    tab = api.get(f'/api/deals/{sold_deal.id}/commission/').json()
    assert tab['booking']['state'] == 'unbooked'


def test_H26_OQ75_one_record_per_carrier_with_the_sold_set_summed(user, sold_deal, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1', 'c2', 'u1')
    cigna, uhc = live(sold_deal)
    assert cigna.carrier == 'Cigna' and sorted(cigna.values['plan_ids']) == sorted(
        [sold_deal.picks['c1'].id, sold_deal.picks['c2'].id]
    )
    assert cigna.values['premium_annual'] == '216000.00'  # (500 + 400) × 20 × 12: the sold set, never one plan
    assert cigna.values['plan_label'] == '2 plans: One · Two'
    assert uhc.values['premium_annual'] == '108000.00'


def test_H28_booking_twice_changes_nothing(user, sold_deal, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1')
    before = Activity.objects.count()
    again = services.book_deal(user, sold_deal.id)
    assert again.changes == [] and again.activity is None
    assert Activity.objects.count() == before


def test_H28_H36_a_rebook_refreshes_sale_keys_and_never_a_typed_one(
    user, sold_deal, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1')
    (record,) = live(sold_deal)
    services.edit_record(user, record.id, {'premium_annual': '119,500', 'policy_number': 'P-1'})
    quotes.update_plan(user, sold_deal.picks['c1'].id, {'values': {'rate_ee': '600'}})
    services.rebook(user, sold_deal.id)
    record.refresh_from_db()
    assert record.values['premium_annual'] == '119500.00'  # typed: kept
    assert record.sources['premium_annual']['origin'] == 'typed'
    assert record.values['policy_number'] == 'P-1'
    assert record.values['employees'] == 20  # a sale key, refreshed (unchanged here)


def test_H28_a_carrier_renamed_on_the_plan_updates_the_record_found_by_its_plans(
    user, sold_deal, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'u1')
    (record,) = live(sold_deal)
    quotes.update_plan(user, sold_deal.picks['u1'].id, {'carrier': 'UHC'})
    services.rebook(user, sold_deal.id)
    assert [r.id for r in live(sold_deal)] == [record.id]
    record.refresh_from_db()
    assert record.carrier == 'UHC'


def test_H32_unselling_voids_the_record_and_selling_again_brings_it_back(
    user, sold_deal, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1', 'u1')
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'u1', sold=False)
    statuses = dict(Record.objects.filter(deal=sold_deal).values_list('carrier', 'status'))
    assert statuses == {'Cigna': 'booked', 'UnitedHealthcare': 'void'}
    uhc = Record.objects.get(deal=sold_deal, carrier='UnitedHealthcare')
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'u1')
    uhc.refresh_from_db()
    assert uhc.status == 'booked'
    assert Record.objects.filter(deal=sold_deal).count() == 2  # never deleted, never doubled


def test_H124_a_lost_deal_never_books(user, sold_deal):
    from deals.services import mark_lost

    mark_lost(user, sold_deal.id, 'Went elsewhere')
    with pytest.raises(activity.Refused):
        quotes.set_sold(user, sold_deal.picks['c1'].id, True)
    with pytest.raises(activity.Refused):
        services.book_deal(user, sold_deal.id)
    assert not Record.objects.filter(deal=sold_deal).exists()


def test_H26_a_kept_line_with_an_in_force_commission_books_beside_the_sale(
    user, sold_deal, django_capture_on_commit_callbacks
):
    CurrentCoverage.objects.create(
        deal=sold_deal,
        line='basic_life_add',
        carrier='Guardian',
        in_force=True,
        on_proposal=True,
        commission={'type': 'pct', 'value': '15'},
        commission_source='carrier',
    )
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1')
    life = Record.objects.get(deal=sold_deal, line='basic_life_add')
    assert life.carrier == 'Guardian' and life.values['rate'] == {'type': 'pct', 'value': '15'}
    assert life.sources['rate']['origin'] == 'in_force'
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1', sold=False)  # the last sold plan: the kept line voids too (H32)
    assert set(Record.objects.filter(deal=sold_deal).values_list('status', flat=True)) == {'void'}


def test_H30_H31_a_later_year_counts_the_earlier_records_and_renews_them(
    user, sold_deal, django_capture_on_commit_callbacks
):
    earlier = services.add_to_book(
        user,
        {
            'client': sold_deal.client_id,
            'line': 'medical',
            'carrier': 'Aetna',
            'effective_date': '2026-01-01',
            'premium_annual': '100000',
            'rate': '4',
        },
    ).record
    assert earlier.year_number == 1  # a Prospect with no earlier record: the first year
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1')
    (record,) = live(sold_deal)
    assert (record.year_number, record.is_renewal) == (2, True)
    earlier.refresh_from_db()
    assert (earlier.status, earlier.term_end.isoformat()) == ('renewed', '2027-01-01')


def test_H30_a_deal_opened_for_an_existing_client_books_year_unknown(user, django_capture_on_commit_callbacks):
    deal = make_deal(user, name='Long-time Co.', relationship='existing_client', effective_date='2027-01-01')
    made = plan(user, deal, 'Cigna', 'One')
    quotes.set_enrollment(user, deal, 'medical', plans=[{'id': made.id, 'enrollment': TIERS['medical']}])
    with django_capture_on_commit_callbacks(execute=True):
        quotes.set_sold(user, made.id, True)
    record = Record.objects.get(deal=deal)
    assert record.year_number is None and record.is_renewal
    tab = selectors.deal_payload(deal, user)
    assert 'year' in tab['booking']['records'][0]['holes']
    services.update(user, deal.id, {'year_number': 4})
    services.rebook(user, deal.id)
    record.refresh_from_db()
    assert record.year_number == 4


def test_H120_counts_that_change_after_the_booking_read_out_of_date_and_update_rebooks(
    user, admin_user, sold_deal, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1')
    current = sold_deal.plans.get(role='current')
    more = {'EE': 20, 'ES': 3, 'EC': 2, 'FAM': 5}
    quotes.set_enrollment(user, sold_deal, 'medical', plans=[{'id': current.id, 'enrollment': more}])
    booking = selectors.deal_payload(sold_deal, admin_user)['booking']
    (stale,) = booking['stale']
    assert set(stale['keys']) >= {'premium_annual', 'employees'}
    assert (stale['before'], stale['after']) == (6000, 9000)
    services.rebook(user, sold_deal.id)
    assert selectors.deal_payload(sold_deal, admin_user)['booking']['stale'] == []


def test_H29_OQ71_a_flat_split_pays_its_amount_once_on_the_deal(
    user, admin_user, sold_deal, django_capture_on_commit_callbacks
):
    from commission.models import Party

    partner = Party.objects.create(kind='partner', name='Riverside Partners (synthetic)')
    flat = {'type': 'flat', 'value': '900'}
    rows = [{'user': user.id, 'role': 'primary'}, {'party': partner.id, 'role': 'split', 'amount': flat}]
    services.save_split(user, deal_id=sold_deal.id, rows=rows)
    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1', 'u1')
    rows = selectors.deal_payload(sold_deal, admin_user)['booking']['records']
    paid = sum(share['amount'] for row in rows for share in row['shares'] if share['party'] == partner.id)
    # Once across the deal's two records, never per record (1,800); a share is whole millionths, so a cent may move.
    assert abs(paid - 900) <= 0.02
    for row in rows:
        assert round(sum(share['amount'] for share in row['shares']), 2) == row['expected']


def test_H36_a_rebook_freezes_the_terms_again_unless_shares_were_typed(
    user, sold_deal, django_capture_on_commit_callbacks
):
    from commission.models import Settings

    with django_capture_on_commit_callbacks(execute=True):
        sell(user, sold_deal, 'c1')
    (record,) = live(sold_deal)
    primary = next(row['party'] for row in record.terms['rows'] if row['role'] == 'primary')
    typed = [{'party': None, 'role': 'house', 'pct': '70'}, {'party': primary, 'role': 'primary', 'pct': '30'}]
    services.set_shares(user, record.id, typed, 'Agreed with the producer')
    Settings.objects.create(pk=1, first_year_pct='50')
    services.rebook(user, sold_deal.id)
    record.refresh_from_db()
    assert record.terms['house_pct'] == '50'  # the terms were frozen again …
    assert record.terms['shares'][0]['pct'] == '70'  # … and the typed shares kept, with their reason
    assert record.terms['reason'] == 'Agreed with the producer'
