"""The Agenda's words and the step catalogue (plan.md §4.6, §5.9; I4, I41–I66, I.6). A data module: served by
/api/meta/ `agenda`, read by the pure step rules (`agenda.steps`) and by the services' Activity summaries.

Each step key has its catalogue `title` (the step's name: Activity and the Later note use it, never the live words with
their counts), the `tab` where its work is done, the `track` it sits on and whether it can `lead` (stand for the deal's
next step). Tracks run in this order: intake, enrollment, quotes, close, after the sale, asks (§5.9). The live words a
row shows are worked out by the rules in `agenda/steps/`, ported from old Vantage 891f1b3 `tasks/steps.py`.
`checklist:<item>` keys share the `checklist:*` entry.
"""

INTAKE, ENROLLMENT, QUOTES, CLOSE, AFTER_SALE, ASKS = 'intake', 'enrollment', 'quotes', 'close', 'after_sale', 'asks'
TRACKS = (INTAKE, ENROLLMENT, QUOTES, CLOSE, AFTER_SALE, ASKS)

# key: (title, tab, track, lead)
STEPS = {
    # The intake gate (I44, I46–I48): shown while the deal is neither marketed nor sold; leads only until quotes are in.
    'complete_intake': ('Complete intake', 'intake', INTAKE, True),
    'checklist:coverage_intent': ('Confirm the coverage and what we are shopping', 'intake', INTAKE, True),
    'checklist:*': ('Checklist item', 'intake', INTAKE, True),
    'checklist_ask': ('Ask the client for checklist items', 'intake', INTAKE, True),
    'review_client_answers': ('Review answers from the client', 'review', INTAKE, True),
    'review_flagged_answers': ('Review flagged answers', 'intake', INTAKE, True),
    'add_hr_contact': ("Add the client's HR contact", 'intake', INTAKE, True),
    'get_bor': ('Get the broker of record letter signed', 'intake', INTAKE, True),
    'questionnaire': ('The medical questionnaire', 'questionnaire', INTAKE, True),
    'finish_intake': ('Finish intake', 'intake', INTAKE, True),
    'send_rfp': ('Intake ready — market for quotes', 'intake', INTAKE, True),
    'build_rfp': ('Build the RFP', 'rfp', INTAKE, False),
    # Enrollment (I49–I51): keeps leading after quotes, so a census that arrives late is mapped and picked up.
    'review_mapping': ('Review column mapping', 'census', ENROLLMENT, True),
    'map_census': ('Map the census', 'census', ENROLLMENT, True),
    'import_census': ('Import the census', 'census', ENROLLMENT, True),
    'fix_census': ('Fix census errors', 'census', ENROLLMENT, True),
    'approve_client': ('Review client-provided values', 'review', ENROLLMENT, True),
    'answer_client_questions': ('Answer questions from the client', 'review', ENROLLMENT, False),
    # Quotes (I53–I55).
    'read_quotes': ('Read carrier quotes', 'advisor', QUOTES, True),
    'follow_up_carriers': ('Follow up with the carriers', 'rfp', QUOTES, False),
    'review_values': ('Review flagged values', 'advisor', QUOTES, True),
    # Close (I56–I60).
    'build_proposal': ('Build the proposal', 'proposal', CLOSE, True),
    'issue_proposal': ('Issue the proposal to the client', 'proposal', CLOSE, True),
    'follow_up_selection': ('Follow up on the proposal', 'proposal', CLOSE, False),
    'mark_sold': ('Mark the winning plan sold', 'advisor', CLOSE, True),
    # After the sale (I63): the workflow ends at commissions.
    'commission': ('Enter the commission', 'commission', AFTER_SALE, True),
    # The client's asks (I64, I65): two steps at most, never one per link.
    'send_drafts': ('Send the requests you drafted', 'review', ASKS, False),
    'follow_up_client': ('Follow up with the client', 'review', ASKS, False),
}

ORDER = list(STEPS)


def entry(key):
    """(title, tab, track, lead) of a step key; `checklist:<item>` keys read the `checklist:*` entry."""
    if key in STEPS:
        return STEPS[key]
    if key.startswith('checklist:'):
        return STEPS['checklist:*']
    return None


def title(key):
    found = entry(key)
    return found[0] if found else key


def known(key):
    return entry(key) is not None


# The five sections (I4, I5): key, title, the one-line description under an open section, and its empty words.
SECTIONS = [
    {'key': 'up_next', 'title': 'Up next', 'sub': 'Ours to do now.', 'empty': 'Nothing to do right now.'},
    {
        'key': 'waiting',
        'title': 'Waiting on',
        'sub': 'With the client or a carrier. A follow-up opens here once a wait runs long.',
        'empty': 'Not waiting on anyone.',
    },
    {'key': 'later', 'title': 'Later', 'sub': 'Held back by someone until the day shown.', 'empty': ''},
    {'key': 'blocked', 'title': 'Blocked', 'sub': 'Waits on a step before it.', 'empty': ''},
    {
        'key': 'done',
        'title': 'Done',
        'sub': 'Finished: by the work itself, ticked, or marked done anyway.',
        'empty': '',
    },
]
SECTION_KEYS = [section['key'] for section in SECTIONS]
COLLAPSED = ('done',)  # Done starts collapsed (I5)

# Who a waiting step waits on, in words (I11).
OWNER_WORDS = {'client': 'the client', 'carrier': 'the carrier', 'us': 'us'}

# The journey's milestones (I69, I120), in order, with the stepper group each sits in. Progress counts those that
# apply; a quote-first deal never counts the Get to Market milestones it skipped.
GET_TO_MARKET, QUOTE_TO_CLOSE = 'get_to_market', 'quote_to_close'
MILESTONES = [
    ('intake_ready', 'Intake ready', GET_TO_MARKET),
    ('enrollment_in', 'Enrollment in', GET_TO_MARKET),
    ('marketed', 'Sent to market', GET_TO_MARKET),
    ('quotes_in', 'Quotes in', QUOTE_TO_CLOSE),
    ('built', 'Proposal built', QUOTE_TO_CLOSE),
    ('issued', 'Proposal issued', QUOTE_TO_CLOSE),
    ('sold', 'Sold', QUOTE_TO_CLOSE),
    ('commission', 'Commission entered', QUOTE_TO_CLOSE),
]
GROUP_LABELS = {GET_TO_MARKET: 'Get to Market', QUOTE_TO_CLOSE: 'Quote to Close'}

# The tab each milestone's dot opens on the stepper (M39; old journey `tab`), and the milestone that owns each lead
# step: the stepper's current dot is the milestone owning the deal's next step, so dot and banner agree (M39, ch. C5).
# A step no milestone owns (the asks) leaves the current dot on the first milestone still to do.
MILESTONE_TABS = {
    'intake_ready': 'intake',
    'enrollment_in': 'census',
    'marketed': 'intake',
    'quotes_in': 'advisor',
    'built': 'proposal',
    'issued': 'proposal',
    'sold': 'advisor',
    'commission': 'commission',
}
STEP_MILESTONES = {
    **dict.fromkeys(
        ('complete_intake', 'checklist_ask', 'review_client_answers', 'review_flagged_answers', 'add_hr_contact',
         'get_bor', 'questionnaire', 'finish_intake'),
        'intake_ready',
    ),
    **dict.fromkeys(('send_rfp', 'build_rfp'), 'marketed'),
    **dict.fromkeys(
        ('review_mapping', 'map_census', 'import_census', 'fix_census', 'approve_client', 'answer_client_questions'),
        'enrollment_in',
    ),
    **dict.fromkeys(('read_quotes', 'follow_up_carriers', 'review_values'), 'quotes_in'),
    'build_proposal': 'built',
    **dict.fromkeys(('issue_proposal', 'follow_up_selection'), 'issued'),
    'mark_sold': 'sold',
    'commission': 'commission',
}  # fmt: skip


def milestone_of(step_key):
    """The milestone a step belongs to, or None (`checklist:<item>` steps are intake's)."""
    if step_key and step_key.startswith('checklist:'):
        return 'intake_ready'
    return STEP_MILESTONES.get(step_key)


# The Overview banner's words when nothing waits on anyone (I119).
WITH_US = 'The ball is in our court'

# A queue row's words when a deal has nothing left and no sale (the old work feed's "Complete").
COMPLETE = 'Complete'

# The Work queue's filters (I78; old homeRows.js), served by /api/meta/ `agenda.queue` so the browser holds no list of
# its own. Type: the deal type as of the deal (`deals.rules.deal_type`, I123); the old Upkeep chip waits with the Radar
# (ch. 21). Due: plain comparisons on each row's `due_in` (days from the agency's today; ch. 12), `None` an open end;
# an undated row matches only All. Category: hand tasks and nudges (ch. 21); deal rows are the pipeline.
QUEUE_TYPES = [{'key': 'all', 'label': 'All work'}, {'key': 'new_business', 'label': 'New business'},
               {'key': 'renewal', 'label': 'Renewals'}]  # fmt: skip
DUE_BUCKETS = [
    {'key': 'overdue', 'label': 'Overdue', 'min': None, 'max': -1},
    {'key': 'week', 'label': 'This week', 'min': 0, 'max': 7},
    {'key': '30', 'label': '30 days', 'min': 0, 'max': 30},
    {'key': '90', 'label': '90 days', 'min': 0, 'max': 90},
    {'key': 'all', 'label': 'All', 'min': None, 'max': None},
]
TASKS = 'task'
CATEGORIES = [{'key': TASKS, 'label': 'Tasks'}]
PIPELINE = {'key': 'pipeline', 'label': 'Pipeline'}

# Row chips (I30, I35).
TASK_CHIP, NUDGE_CHIP = 'Task', 'Nudge'
NUDGE_TITLE = 'Nudge {who} about their form'
NUDGE_NO_NAME = 'the client'
