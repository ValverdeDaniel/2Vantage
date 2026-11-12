"""The split's rules, pure (plan.md §5.6; H10, H19, H30): validation in the old words, the resolver's order, the
producer share and the year a deal pays in."""

from decimal import Decimal
from types import SimpleNamespace

from commission import rules

PEOPLE = {
    ('party', 1): {'kind': 'producer', 'appointed': True, 'login': False, 'active': True},
    ('party', 2): {'kind': 'producer', 'appointed': False, 'login': False, 'active': True},
    ('party', 3): {'kind': 'partner', 'appointed': False, 'login': False, 'active': True},
    ('party', 4): {'kind': 'partner', 'appointed': False, 'login': False, 'active': False},
    ('user', 9): {'kind': 'producer', 'appointed': False, 'login': True, 'active': True},
}
PCT = lambda value: {'type': 'pct', 'value': str(value)}  # noqa: E731


def check(rows):
    return rules.validate_rows(rows, PEOPLE)


def test_H19_a_clean_split_keeps_its_terms_and_puts_the_primary_first():
    rows, errors = check(
        [
            {'party': 3, 'role': 'referral', 'amount': '10', 'basis': 'gross', 'works_it': True},
            {'user': 9, 'role': 'primary'},
            {'party': 1, 'role': 'secondary', 'amount': PCT(40), 'renewal_amount': '', 'expires_after_years': '3'},
        ]
    )
    assert errors == {}
    assert rows[0] == {
        'user': 9,
        'role': 'primary',
        'amount': None,
        'renewal_amount': None,
        'basis': 'pool',
        'expires_after_years': None,
        'works_it': False,
    }
    assert rows[1]['amount'] == PCT(10) and rows[1]['basis'] == 'gross'
    assert rows[1]['works_it'] is False  # a referral agent never "works it"
    assert rows[2]['expires_after_years'] == 3 and rows[2]['renewal_amount'] is None


def test_H19_exactly_one_appointed_producer_is_the_primary():
    assert check([]) == ([], {'rows.primary': rules.PICK_PRIMARY})
    assert check([{'party': 1, 'role': 'secondary', 'amount': '5'}])[1] == {'rows.primary': rules.PICK_PRIMARY}
    _rows, errors = check([{'party': 1, 'role': 'primary'}, {'user': 9, 'role': 'primary'}])
    assert errors == {'rows.primary': rules.ONE_PRIMARY}
    assert check([{'party': 2, 'role': 'primary'}])[1] == {'rows.0.party': rules.PRIMARY_APPOINTED}
    assert check([{'party': 3, 'role': 'primary'}])[1] == {'rows.0.party': rules.PRIMARY_KIND}


def test_H12_each_role_takes_its_kinds_of_party():
    base = {'party': 1, 'role': 'primary'}
    assert check([base, {'party': 3, 'role': 'secondary', 'amount': '5'}])[1] == {'rows.1.party': rules.SECONDARY_KIND}
    assert check([base, {'user': 9, 'role': 'referral', 'amount': '5'}])[1] == {'rows.1.party': rules.REFERRAL_KIND}
    assert check([base, {'party': 3, 'role': 'split', 'amount': '5'}])[1] == {}


def test_H19_people_amounts_and_totals():
    base = {'party': 1, 'role': 'primary'}
    errors = check(
        [
            base,
            {'party': 99, 'role': 'split', 'amount': '5'},
            {'party': 4, 'role': 'split', 'amount': '5'},
            {'party': 1, 'role': 'split', 'amount': '5'},
            {'party': 3, 'role': 'boss', 'amount': '5'},
        ]
    )[1]
    assert errors == {
        'rows.1.party': rules.PICK_PERSON,
        'rows.2.party': rules.PICK_PERSON,  # an inactive partner cannot be picked
        'rows.3.party': rules.TWICE,
        'rows.4.role': rules.UNKNOWN_ROLE,
    }
    errors = check([base, {'user': 9, 'role': 'split', 'amount': '', 'basis': 'net', 'expires_after_years': '0'}])[1]
    assert errors == {
        'rows.1.amount': rules.NO_AMOUNT,
        'rows.1.basis': rules.BAD_BASIS,
        'rows.1.expires_after_years': rules.BAD_YEARS,
    }
    assert check([base, {'party': 3, 'role': 'split', 'amount': '101'}])[1] == {
        'rows.1.amount': 'Must be between 0 and 100'
    }
    pool = check([base, {'party': 3, 'role': 'split', 'amount': '60'}, {'user': 9, 'role': 'split', 'amount': '41'}])
    assert pool[1] == {'rows.split_total': rules.POOL_OVER}
    gross = [base, {'party': 3, 'role': 'split', 'amount': '60', 'basis': 'gross'}]
    gross.append({'user': 9, 'role': 'split', 'amount': '40', 'basis': 'gross'})
    assert check(gross)[1] == {'rows.split_total': rules.GROSS_OVER}


def test_H10_the_resolver_order():
    deal_rows, client_rows = [{'party': 1, 'role': 'primary'}], [{'party': 2, 'role': 'primary'}]
    assert rules.resolve(deal_rows, client_rows, {'party': 5}, {'party': 6}) == ('deal', deal_rows)
    assert rules.resolve(None, client_rows, {'party': 5}, {'party': 6}) == ('client', client_rows)
    source, rows = rules.resolve(None, [], {'user': 5}, {'party': 6})
    assert source == 'deal_owner' and rows[0]['user'] == 5 and rows[0]['role'] == 'primary'
    assert rules.resolve(None, None, None, {'party': 6})[0] == 'client_owner'
    assert rules.resolve(None, None, None, None) == ('house', [])


def test_H97_the_producer_share_is_the_primarys_own_else_the_firm_default():
    settings = SimpleNamespace(first_year_pct=Decimal(40), renewal_pct=Decimal(30))
    assert rules.producer_pct({'first_year_pct': '55', 'renewal_pct': None}, settings, True) == (Decimal(55), 'party')
    assert rules.producer_pct({'first_year_pct': '55', 'renewal_pct': None}, settings, False) == (
        Decimal(30),
        'default',
    )
    assert rules.producer_pct(None, settings, True) == (Decimal(40), 'default')


def test_H30_the_year_before_any_record():
    assert rules.year_number(3, 'existing_client') == 3
    assert rules.year_number(None, 'prospect') == 1
    assert rules.year_number(None, 'new_client') == 1
    assert rules.year_number(None, 'existing_client') is None  # renewal terms, "year unknown"
