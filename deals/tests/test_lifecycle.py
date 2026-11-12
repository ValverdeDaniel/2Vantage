"""deals.lifecycle, the client status's pure table (plan.md §5.1; CL1–CL9). Every row of the move table."""

import pytest

from deals import lifecycle

P, N, E = lifecycle.PROSPECT, lifecycle.NEW_CLIENT, lifecycle.EXISTING_CLIENT
LOST = 'This deal is marked lost — reopen it before converting the client.'
SOLD = 'A plan is marked sold — un-sell it first.'
FIRST_RENEWAL = "A new client becomes existing with its first renewal, which this version doesn't build yet."
PAST_FIRST_YEAR = 'An existing client is past its first year.'

# (from, to, has_sold, lost) -> the refusal, None when allowed.
HAND = [
    (P, N, False, False, None),  # Convert to client
    (P, N, False, True, LOST),
    (N, P, False, False, None),  # Back to prospect
    (N, P, True, False, SOLD),
    (E, P, False, False, None),  # Back to prospect also fixes a wrong Existing pick
    (E, P, True, False, SOLD),
    (P, E, False, False, None),  # a classification fix
    (P, E, False, True, None),
    (N, E, False, False, FIRST_RENEWAL),  # deferred with renewals (OQ1, CL7)
    (N, E, True, False, FIRST_RENEWAL),
    (E, N, False, False, PAST_FIRST_YEAR),
    (E, N, True, True, PAST_FIRST_YEAR),
    (P, P, False, True, None),  # a move to the current status is allowed and writes nothing
    (N, N, True, False, None),
]


@pytest.mark.parametrize('current, to, has_sold, lost, refusal', HAND)
def test_CL4_CL5_CL7_each_hand_move_is_allowed_or_refused_with_its_sentence(current, to, has_sold, lost, refusal):
    assert lifecycle.refusal(current, to, has_sold=has_sold, lost=LOST if lost else None) == refusal


@pytest.mark.parametrize(
    'current, to, action, summary',
    [
        (P, N, 'converted', 'Converted to a client'),
        (N, P, 'prospect', 'Moved back to a prospect'),
        (E, P, 'prospect', 'Moved back to a prospect'),
        (P, E, 'status', 'Marked as an existing client'),
    ],
)
def test_CL4_CL5_each_allowed_hand_move_has_its_activity_action_and_summary(current, to, action, summary):
    assert lifecycle.hand_move(current, to) == (action, summary)


# (status, converted_by_sale, any_sold) -> the status the sale or un-sale leaves, None for no change.
SALES = [
    (P, False, True, N),  # a sale converts a prospect (CL2)
    (N, True, True, None),  # a second sold plan changes nothing
    (N, True, False, P),  # un-selling the last sold plan undoes the sale's conversion (CL3)
    (N, False, False, None),  # a hand conversion survives an un-sell
    (N, False, True, None),
    (E, False, True, None),  # existing clients ignore sales
    (E, False, False, None),
    (P, False, False, None),
]


@pytest.mark.parametrize('current, by_sale, any_sold, after', SALES)
def test_CL2_CL3_a_sale_converts_a_prospect_and_un_selling_undoes_only_a_sales_conversion(
    current, by_sale, any_sold, after
):
    assert lifecycle.after_sale(current, by_sale, any_sold) == after


@pytest.mark.parametrize(
    'status, refusal',
    [(P, None), (E, None), (N, 'A prospect becomes a new client when a plan is sold, or with Convert to client.')],
)
def test_CL6_a_client_is_created_as_a_prospect_or_an_existing_client(status, refusal):
    assert lifecycle.creation_refusal(status) == refusal
    assert lifecycle.creation_refusal('new') == lifecycle.UNKNOWN


def test_CL9_the_dialog_moves_list_every_other_status_with_its_sentence():
    assert lifecycle.moves(N, has_sold=True) == [
        {'to': P, 'label': 'Back to prospect', 'allowed': False, 'sentence': SOLD},
        {'to': E, 'label': 'Mark as an existing client', 'allowed': False, 'sentence': FIRST_RENEWAL},
    ]
    assert lifecycle.moves(P, has_sold=False, lost=LOST) == [
        {'to': N, 'label': 'Convert to client', 'allowed': False, 'sentence': LOST},
        {'to': E, 'label': 'Mark as an existing client', 'allowed': True, 'sentence': ''},
    ]


def test_CL9_an_unknown_status_is_refused():
    assert lifecycle.refusal(P, 'existing', has_sold=False) == lifecycle.UNKNOWN
