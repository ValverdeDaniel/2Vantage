"""`presented()` and `room()` (plan.md §5.4; F50, F119, J2, J3; OQ11), table-driven over plain plans."""

import pytest

from quotes import presented
from quotes.shapes import LineData, PlanData


def line(*specs):
    """specs: (role, marks) with marks any of 's' (starred) and 'r' (recommended); ids from 1 in order."""
    plans = [
        PlanData(
            id=i, role=role, starred='s' in marks, recommended='r' in marks, sort_order=i, carrier='C', name=f'P{i}'
        )
        for i, (role, marks) in enumerate(specs, start=1)
    ]
    return LineData('composite', plans)


@pytest.mark.parametrize(
    'case, specs, ids',
    [
        ('no star: every plan', [('current', ''), ('renewal', ''), ('alternate', ''), ('alternate', '')], [1, 2, 3, 4]),
        ('stars: current and starred', [('current', ''), ('alternate', 's'), ('alternate', '')], [1, 2]),
        (
            'OQ11: a starred line prints its renewal only when picked',
            [('current', ''), ('renewal', ''), ('alternate', 's')],
            [1, 3],
        ),
        ('a recommended renewal prints', [('current', ''), ('renewal', 'r'), ('alternate', 's')], [1, 2, 3]),
        (
            'a recommended quote prints without a star',
            [('current', ''), ('alternate', 'r'), ('alternate', 's')],
            [1, 2, 3],
        ),
        ('no current plans, stars', [('alternate', 's'), ('alternate', '')], [1]),
        ('an empty line', [], []),
    ],
)
def test_F119_presented_is_current_recommended_and_starred_or_every_plan(case, specs, ids):
    assert [p.id for p in presented.presented(line(*specs))] == ids, case


def test_J2_a_line_kept_off_the_proposal_presents_nothing():
    assert presented.presented(line(('current', ''), ('alternate', 's')), off=True) == []


@pytest.mark.parametrize(
    'case, specs, room',
    [
        ('three current plans', [('current', '')] * 3, 13),
        (
            'current, recommended and starred all count',
            [('current', '')] * 3 + [('alternate', 'r'), ('alternate', 's')],
            11,
        ),
        ('a recommended star counts once', [('current', '')] + [('alternate', 'rs')], 14),
        ('unpicked quotes take no room', [('current', '')] + [('alternate', '')] * 20, 15),
        ('full', [('current', '')] * 4 + [('alternate', 's')] * 12, 0),
    ],
)
def test_F50_room_counts_every_column_a_starred_line_presents(case, specs, room):
    assert presented.room(line(*specs)) == room, case


def test_J3_a_line_with_no_stars_may_present_more_than_16():
    many = line(*[('alternate', '')] * 20)
    assert len(presented.presented(many)) == 20 and presented.room(many) == 16


def test_F50_the_refusal_names_what_the_line_holds():
    full = line(*[('current', '')] * 3, ('renewal', 'r'), *[('alternate', 's')] * 12)
    assert presented.refusal(full, 'Medical', 1) == (
        'The Medical proposal holds 16 plans (3 current, 1 recommended, 12 starred) — unstar one first.'
    )
    nearly = line(*[('current', '')] * 3, *[('alternate', 's')] * 12)
    assert presented.refusal(nearly, 'Medical', 1) is None
    assert presented.refusal(nearly, 'Medical', 3) == (
        'The Medical proposal holds 16 plans (3 current, 12 starred): 3 ticked, only 1 more fit. '
        'Unstar some or tick fewer.'
    )
