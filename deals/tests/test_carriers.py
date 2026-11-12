"""deals.carriers: the registry and the three-tier matcher (plan.md §4.7; F14, K104, K105). Cases from old Vantage."""

import pytest

from deals import carriers


@pytest.mark.parametrize(
    'name, key',
    [
        ('UHC', 'unitedhealthcare'),
        ('United Healthcare', 'unitedhealthcare'),
        ('UnitedHealthcare of Florida', 'unitedhealthcare'),
        ('UHC Level-Funded', 'unitedhealthcare'),
        ('BCBS FL', 'florida_blue'),
        ('BlueCross BlueShield', 'florida_blue'),
        ('Blue Cross Blue Shield of Florida', 'florida_blue'),
        ('Blue Cross and Blue Shield of Florida, Inc.', 'florida_blue'),
        ('Aetna Life Insurance Co.', 'aetna'),
        ('Guardian Life Insurance Company', 'guardian'),
        ('SunLife', 'sun_life'),
        ('United Concordia (Dental)', 'united_concordia'),
    ],
)
def test_K105_spellings_reach_their_carrier(name, key):
    assert carriers.match(name) == key


@pytest.mark.parametrize('name', ['United of Omaha', 'BCBS of Illinois', 'VSP', 'Unknown carrier', '', None])
def test_K105_generic_and_unknown_names_match_nothing(name):
    assert carriers.match(name) is None


def test_K105_every_registry_form_reaches_its_own_carrier():
    for carrier in carriers.CARRIERS:
        for form in (carrier['key'], carrier['name'], *carrier['aliases']):
            assert carriers.match(form) == carrier['key'], form


def test_K105_identity_groups_spellings_and_skips_blanks():
    assert carriers.identity('UHC') == carriers.identity('UnitedHealthcare') == 'unitedhealthcare'
    assert carriers.identity('VSP') == carriers.identity('VSP Inc.') == 'n:vsp'
    assert carriers.identity('VSP') != carriers.identity('VSP Vision Care')
    assert carriers.identity('Unknown carrier') == carriers.identity('') == ''
    assert carriers.norm('The Insurance Company') == 'the insurance company'  # all corporate words: kept whole


def test_K105_display_name_is_the_registrys_spelling_when_matched():
    assert carriers.display_name('uhc') == 'UnitedHealthcare'
    assert carriers.display_name('  Oscar Health ') == 'Oscar Health'


@pytest.mark.parametrize(
    'text, names',
    [
        ('Oscar Health, Mutual of Omaha; UHC\nUHC', ['Oscar Health', 'Mutual of Omaha', 'UHC']),
        ('Morgan White Group & Co.', ['Morgan White Group & Co.']),
        ('Delta Dental and VSP', ['Delta Dental', 'VSP']),
        ('Cigna & UHC / UnitedHealthcare', ['Cigna', 'UHC']),
        ('', []),
    ],
)
def test_K104_split_names_reads_a_box_of_carriers(text, names):
    assert carriers.split_names(text) == names


def test_K104_a_name_is_at_most_sixty_characters():
    assert carriers.split_names('A' * 80) == ['A' * 60]


def test_F14_the_registry_has_unique_keys_and_the_finders_aliases():
    keys = [carrier['key'] for carrier in carriers.CARRIERS]
    assert len(keys) == len(set(keys))
    assert {carrier['group'] for carrier in carriers.CARRIERS} == {'medical', 'ancillary'}
    assert 'UHC' in carriers.BY_KEY['unitedhealthcare']['aliases']
