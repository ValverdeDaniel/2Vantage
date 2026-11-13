"""Review's words (rule 1; L133: words come from /api/meta/, never twinned in JS). A data module: old Vantage's
labels and refusals (891f1b3 `reviewrequest/registry.py`, `RequestCard.jsx`, `LinkStatus.jsx`,
`LinkSettingsCard.jsx`, `market/client_request.py`), served by `review.meta.meta()`."""

# Who can open a link (old LINK_LEVELS and ACCESS_WORDS; the emailed code waits for outbound mail, L65).
LEVELS = [
    {
        'key': 'link',
        'label': 'Private link',
        'means': 'Anyone holding the link can open it',
        'help': 'An unguessable link that works until it expires. Whoever holds it can open it, so a forwarded link '
        'forwards the access.',
    },
    {
        'key': 'pin',
        'label': 'PIN required',
        'means': 'Opens only with the PIN you gave them',
        'help': 'Before anything shows, the person types a 6-digit PIN you give them yourself, so a forwarded link is '
        'useless without it. Five wrong tries lock it until you make a new one.',
    },
]
LEVEL_NEEDS = {'pin': 'a PIN'}

# One request, from its links (old RequestCard STATE_LABELS).
REQUEST_STATES = [
    ('draft', 'Not sent yet'),
    ('partly_sent', 'Partly sent'),
    ('waiting', 'Waiting on them'),
    ('answered', 'Answered'),
    ('expired', 'Expired unanswered'),
    ('closed', 'Closed'),
]

# One link (old LinkStatus LABELS, plus a closed request's).
LINK_STATES = [
    ('answered', 'Sent back'),
    ('off', 'Turned off'),
    ('closed', 'Request closed'),
    ('covered', 'A colleague answered'),
    ('draft', 'Not sent yet'),
    ('lapsed_draft', 'Expired — never sent'),
    ('expired', 'Expired unanswered'),
    ('opened', 'Opened'),
    ('waiting', 'Waiting'),
]

CLOSE_REASONS = [
    ('answered_elsewhere', 'Answered another way'),
    ('superseded', 'Replaced by a newer request'),
    ('cancelled', 'Cancelled'),
]
CLOSE_LABELS = dict(CLOSE_REASONS)

# The minimal New link's choices of what to ask (L40; slice 57 brings the full Ask list).
INTAKE_SCOPES = [
    ('required', 'What marketing still needs'),
    ('missing', 'Every blank question'),
    ('all', 'The whole intake form'),
]
CENSUS_SCOPES = [
    ('missing', 'The required census gaps'),
    ('blank', 'Every blank in the census'),
    ('all', 'The whole census, to confirm'),
]

# The board's readiness chip: the deal's intake readiness, as the old workspace named it (CaseWorkspace READY_CHIP).
READINESS = [('blocked', 'Intake open'), ('ready', 'Ready to market'), ('submitted', 'Sent to market')]

# Refusals (409 with a sentence, or 400 keyed by field).
LINK_OFF = 'This link is turned off: turn it back on first.'
REQUEST_CLOSED = 'That request is closed: send a new one.'
PAST_LIMIT = 'This link is past its 30-day limit, so it cannot open again: make a new link instead.'
NO_LONGER = (
    'This link cannot live any longer: a link lives at most 30 days from the day it was made. Send a new request '
    'instead.'
)
OPENED = 'This link was opened — it went out.'
NOT_PIN = 'This link does not ask for a PIN.'
PIN_KEPT = 'A PIN is shown once and never kept, so it cannot be put back: make a new one if this one is lost.'
BAD_LEVEL = 'That is not a way to protect a link.'
BAD_DATE = 'Send the date as YYYY-MM-DD.'
DATE_PASSED = 'That date has passed. To stop the link working now, turn it off.'
TOO_LATE = 'A link lives at most 30 days from the day it was made: {day} at the latest.'
MESSAGE_LONG = 'Keep the message under {limit} characters.'
TOO_MANY = 'One request can go to up to {limit} people.'
NOT_A_CONTACT = '{value} is not a contact of this client.'
NAME_NEEDED = 'Give each person you type a name.'
NOT_AN_EMAIL = '{value} is not an email address.'
BAD_PERSON = 'Send each person as {contact_id} or {name, email}.'
BAD_REASON = 'Close it as one of: {reasons}.'
CELLS_ELSEWHERE = 'Some of those census values are not on this deal: {ids}.'
UNKNOWN_ACTION = 'Send an action: {actions}.'

# The review queue (slice 55; old 891f1b3 `reviewrequest/vocab.py` CHANGE_KINDS, `CensusClientReview.jsx` phases).
CHANGES = [
    ('changed', 'Changed'),
    ('added', 'New person'),
    ('filled', 'Filled in'),
    ('cleared', 'Cleared'),
    ('same', 'Confirmed as is'),
]
PHASES = [
    ('to_review', 'To review', 'Answers the client submitted, waiting on your decision'),
    ('in_progress', 'Not submitted yet', 'What the client has typed but not submitted yet: read only until they do'),
    ('going_back', 'Going back', 'Answers sent back to the client: they return here when the client answers again'),
]
QUEUE_SECTIONS = [('census', 'Census · client'), ('intake', 'Intake'), ('questionnaire', 'Questionnaire')]

# Notes, the tray and the request page (slice 56; old 891f1b3 `NoteThread.jsx` KIND_WORDS, `RequestRail.jsx` STATUS,
# `FollowUpSnippet.jsx` SECTIONS).
NOTE_KINDS = [
    ('note', 'Note'),
    ('sendback', 'Sent back'),
    ('ask', 'Asked for'),
    ('question', 'Asked'),
    ('reply', 'Replied'),
]
RAIL_STATUSES = [
    ('question', 'Question open'),
    ('in_cart', 'In the tray'),
    ('answered', 'Answered'),
    ('asked', 'Asked'),
    ('on_file', 'On file'),
    ('missing', 'Missing'),
]
TRAY_SECTIONS = [
    ('census', 'Census'),
    ('intake', 'Intake'),
    ('questionnaire', 'Questionnaire'),
    ('documents', 'Documents'),
]
REQUEST_PANES = [
    ('intake', 'Intake'),
    ('census', 'Census'),
    ('questionnaire', 'Questionnaire'),
    ('documents', 'Documents'),
]

# The sections' boards (slice 57; old 891f1b3 `CensusReviewFieldRow.jsx` REQ_BUTTONS, `censusReviewRows.js`
# STATUS_TITLE, `IntakeReviewView.jsx` REQ_BUTTONS and its status chips).
RULES = [('auto', 'Auto'), ('required', 'Required'), ('waived', 'Waived')]  # a census column's (C27, OQ17)
INTAKE_RULES = [('', 'Auto'), ('required', 'Required'), ('waived', 'Waived')]  # an intake question's (B37)
BOARD_STATUSES = [
    ('gap', 'Needed, blank'),
    ('pending', 'From the client'),
    ('answered', 'Answered'),
    ('optional', 'Blank (optional)'),
    ('waived', 'Waived'),
]
CENSUS_SEGMENTS = [
    ('missing', 'Missing — required on this deal'),
    ('na', 'Blank — not required here'),
    ('low', 'Read from a document, unverified'),
    ('client', 'Supplied by the client, pending approval'),
    ('high', 'Filled'),
]

# Next → (L3, L4; old 891f1b3 `DealReviewTab.jsx` KIND_WORDS): what kind of thing comes first.
NEXT_KINDS = [
    ('blocks_carrier', 'Blocks a carrier'),
    ('link_expiring', 'Link running out'),
    ('question', 'Client question'),
    ('oldest', 'Waiting longest'),
]
