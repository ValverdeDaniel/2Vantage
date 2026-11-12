"""The client status, Prospect → New client → Existing client, and its moves (plan.md §5.1; OQ2, OQ101; CL1–CL9).

Pure: no database. `deals.services.set_status` (the status door) and `deals.services.sale_changed` (called by quotes'
`set_sold` inside the sale's transaction) are the only writers, and both ask this table. A client's status is a client
fact; the deal type (New business or Renewal) is `rules.deal_type` over `Deal.opened_as`.
"""

PROSPECT = 'prospect'
NEW_CLIENT = 'new_client'
EXISTING_CLIENT = 'existing_client'

# Served by /api/meta/ as `relationships` (rule 1); screens say "Status".
STATUSES = [(PROSPECT, 'Prospect'), (NEW_CLIENT, 'New client'), (EXISTING_CLIENT, 'Existing client')]
KEYS = [key for key, _ in STATUSES]
LABELS = dict(STATUSES)

# A client is created as a Prospect or an Existing client; New client is reached only by a sale or Convert (CL6).
CREATE_AS = (PROSPECT, EXISTING_CLIENT)
CREATE_NEW_CLIENT = 'A prospect becomes a new client when a plan is sold, or with Convert to client.'
UNKNOWN = 'Status must be Prospect, New client or Existing client.'

# What the client dialog calls each move (the button), by where it goes.
MOVE_LABELS = {
    NEW_CLIENT: 'Convert to client',
    PROSPECT: 'Back to prospect',
    EXISTING_CLIENT: 'Mark as an existing client',
}

# Hand moves through the status door: (from, to) -> (Activity action, summary).
HAND_MOVES = {
    (PROSPECT, NEW_CLIENT): ('converted', 'Converted to a client'),
    (NEW_CLIENT, PROSPECT): ('prospect', 'Moved back to a prospect'),
    (EXISTING_CLIENT, PROSPECT): ('prospect', 'Moved back to a prospect'),
    (PROSPECT, EXISTING_CLIENT): ('status', 'Marked as an existing client'),
}
NEVER = {
    # Deferred with renewals (OQ1, CL7): when the first plan year ends or the first renewal starts.
    (NEW_CLIENT, EXISTING_CLIENT): "A new client becomes existing with its first renewal, which this version doesn't "
    'build yet.',
    (EXISTING_CLIENT, NEW_CLIENT): 'An existing client is past its first year.',
}
SOLD = 'A plan is marked sold — un-sell it first.'

# The automatic moves a sale makes (CL2, CL3): (Activity action, summary). Their rows refuse Revert.
SALE_CONVERTED = ('converted', 'Now a new client (a plan was sold)')
SALE_UNDONE = ('prospect', 'Back to a prospect (no plan is sold now)')
UNDO_SALE = 'Un-sell the plan to undo this.'
UNDO_UNSALE = 'Mark the plan sold again to undo this.'

ACTIONS = ('converted', 'prospect', 'status')


def label(status):
    return LABELS.get(status, status)


def meta():
    """/api/meta/ `relationships`: each status, and whether the New client dialog may create a client with it."""
    return [{'key': key, 'label': text, 'create': key in CREATE_AS} for key, text in STATUSES]


def creation_refusal(status):
    """None when a client may be created with this status, else the sentence (a 400 on `relationship`)."""
    if status == NEW_CLIENT:
        return CREATE_NEW_CLIENT
    if status not in CREATE_AS:
        return UNKNOWN
    return None


def refusal(current, to, *, has_sold, lost=None):
    """None when the hand move is allowed (a move to the current status is allowed and writes nothing), else the
    sentence of its 409. `has_sold`: any plan on any of the client's deals is sold (`providers.client_has_sold`).
    `lost`: `rules.convert_refusal(deals)`, the sentence refusing Convert while the client's deal is lost."""
    if to not in LABELS:
        return UNKNOWN
    if to == current:
        return None
    if (current, to) in NEVER:
        return NEVER[(current, to)]
    if to == PROSPECT and has_sold:
        return SOLD
    if to == NEW_CLIENT and lost:
        return lost
    return None


def hand_move(current, to):
    """(action, summary) of an allowed hand move."""
    return HAND_MOVES[(current, to)]


def after_sale(current, converted_by_sale, any_sold):
    """The status a sale or un-sale leaves, or None when it changes nothing.

    A sale converts a Prospect (CL2). Un-selling the last sold plan across the client's deals returns a client the sale
    converted to Prospect (CL3); a hand conversion, an Existing client and a client with another sold plan are left
    alone. Existing clients ignore sales.
    """
    if any_sold and current == PROSPECT:
        return NEW_CLIENT
    if not any_sold and current == NEW_CLIENT and converted_by_sale:
        return PROSPECT
    return None


def moves(current, *, has_sold, lost=None):
    """The moves the client dialog offers, each allowed or refused with its sentence (worked out here, never in JS)."""
    out = []
    for to in KEYS:
        if to == current:
            continue
        sentence = refusal(current, to, has_sold=has_sold, lost=lost)
        out.append({'to': to, 'label': MOVE_LABELS[to], 'allowed': sentence is None, 'sentence': sentence or ''})
    return out

