"""Deal rules other apps read (plan.md §5.1, §3.6; O.3.7, O.6 #21, #25, #42). Pure: each takes what it reads.

- `refuses(deal, action)`: what a lost deal refuses, each with its sentence (A19). Internal edits pass: lost is a label,
  not a lock. Every caller answers the sentence as a 409 (`deals.activity.Refused`).
- `deal_type(deal)`: New business or Renewal, over `Deal.opened_as` (M14, H30, CL8).
- `agent_name(deal)`: who the carrier forms print as the agent (M27, OQ45): the deal's agent of record, else the
  owner, else the agency producer.
- `is_past(deal, today)` and `client_asks_open(deal, today)`: whether the client may still be asked for anything and
  write through a link (O.6 #31; M9, M49, L56, K64). Staff asks answer the sentence as a 409, portal writes as a 410.
"""

from datetime import timedelta

from . import clock
from .lifecycle import EXISTING_CLIENT

LOST = 'lost'

# What a lost deal refuses (§5.1, O.3.7), with the sentence each refusal answers. The sentences follow old Vantage's
# (891f1b3): "This deal is marked lost — reopen it before …".
REFUSALS = {
    'send_to_market': 'This deal is marked lost — reopen it before sending it to market.',
    'sign': 'This deal is marked lost — reopen it before signing.',
    'mark_sold': 'This deal is marked lost — reopen it before selling a plan.',
    'book': 'This deal is marked lost — reopen it before booking its commission.',
    'portal_write': 'This link is no longer active.',
    'client_ask': 'This deal is marked lost — reopen it before asking the client for anything.',
    'ai_land': 'This deal is marked lost, so the read was saved for review instead of applied. Reopen the deal to use '
    'it.',
    'convert': 'This deal is marked lost — reopen it before converting the client.',
}
ACTIONS = tuple(REFUSALS)

NEW_BUSINESS = 'new_business'
RENEWAL = 'renewal'
DEAL_TYPES = [(NEW_BUSINESS, 'New business'), (RENEWAL, 'Renewal')]
DEAL_TYPE_LABELS = dict(DEAL_TYPES)


def refuses(deal, action):
    """None when `deal` allows `action`, else the sentence. An unknown action is a programming error."""
    if action not in REFUSALS:
        raise ValueError(f'Not an action a lost deal refuses: {action}')
    if deal is not None and deal.stage == LOST:
        return REFUSALS[action]
    return None


def convert_refusal(deals):
    """Convert to client's refusal when one of the client's deals is lost, else None (v1: one deal per client)."""
    return next((refuses(deal, 'convert') for deal in deals if refuses(deal, 'convert')), None)


def deal_type(deal):
    """'renewal' only when the deal opened for an Existing client; otherwise 'new_business'. `opened_as` follows the
    client's status while no plan on the deal is sold, then freezes, so a won prospect's deal stays New business."""
    return RENEWAL if deal.opened_as == EXISTING_CLIENT else NEW_BUSINESS


def deal_type_label(deal):
    return DEAL_TYPE_LABELS[deal_type(deal)]


def agent_name(deal, agency=None):
    """The agent the carrier forms print: the deal's agent of record, else `agent_default` ('' when none).
    `agency` is the settings row, read when needed and not given."""
    return deal.agent_of_record.strip() or agent_default(deal, agency)


def agent_default(deal, agency=None):
    """What a blank agent of record prints, shown in grey beside it: the deal's owner, else
    `AgencySettings.producer_name`."""
    owner = deal.owner
    if owner is not None:
        return owner.get_full_name() or owner.username
    if agency is None:
        from .models import AgencySettings

        agency = AgencySettings.get()
    return agency.producer_name


# A deal is past asking its client a year after its effective date (old Vantage's STALE_AFTER_DAYS, 891f1b3).
PAST_AFTER = timedelta(days=365)
ASKS_CLOSED = {
    'lost': REFUSALS['client_ask'],
    'archived': 'This client is archived — restore it before asking the client for anything.',
    'past': "This is a past or closed year — a link minted here would collect this year's answers onto last year's "
    'deal.',
}


def is_past(deal, today=None):
    """True when the deal is past working with its client (old `is_past_deal`): lost, or more than a year past its
    effective date. Version 1 has no `complete` stage."""
    if deal.stage == LOST:
        return True
    today = today or clock.today()
    return deal.effective_date is not None and deal.effective_date < today - PAST_AFTER


def is_archived(deal):
    """A deal is archived with its client (O.6 #17): there is no `Deal.archived_at` while a client has one deal."""
    return deal.client.archived_at is not None


def client_asks_open(deal, today=None):
    """None while the client may be asked for something and write through its links; else the sentence why not:
    a lost deal, an archived client or a past year (one rule replacing old Vantage's `historical`, C16). Callers answer
    a staff ask with 409 and a portal write with 410; links stay readable (OQ46)."""
    if deal.stage == LOST:
        return ASKS_CLOSED['lost']
    if is_archived(deal):
        return ASKS_CLOSED['archived']
    if is_past(deal, today):
        return ASKS_CLOSED['past']
    return None
