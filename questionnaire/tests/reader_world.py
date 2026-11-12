"""A synthetic filled Florida Blue 51+ form for the questionnaire reader's tests (plan.md §12.1, Q.6, Q.8): a PDF made
by code, Claude's recorded answer for it, and the canary strings that must never leave the questionnaire (medical
answers). Every name and number is invented."""

import hashlib

import synthetic_files
from ai.services import start_read
from documents.tests.helpers import stored

FL, SIIA = 'fl_blue_51', 'stop_loss_siia'
MEDICAL, ILLNESS, CLAIMANT = 'CANARY-MED-5521 dialysis', 'CANARY-MED-8812 chemotherapy', 'CANARY-RISK-Q7'
CANARIES = ('CANARY-MED', 'CANARY-RISK', 'dialysis', 'chemotherapy')

PAGE = [
    'Florida Blue Underwriting Questionnaire (synthetic, filled)',
    '8. Total average employees: 61   10. Florida Blue in the past 24 months: No',
    '12. Reason for bid: Renewal Increase   11. Carrier switches: 2',
    'Plan 1: BlueOptions 1   Current premium 41250',
    f'16. Conditions: Cancer / Breast Cancer, 1 individual, {ILLNESS}',
    f'Comments: {MEDICAL}',
]


def answer(key, value, page=1, unsure=False):
    return {'key': key, 'value': value, 'page': page, 'unsure': unsure}


def value(key, text, unsure=False):
    return {'key': key, 'value': text, 'unsure': unsure}


def condition(illness=ILLNESS, people='1', unsure=False):
    return {
        'block': 'conditions',
        'page': 1,
        'values': [
            value('drpMedCat', 'Cancer'),
            value('drpMedCondition', 'Breast Cancer'),
            value('numNumEEMedCon', people, unsure=unsure),
            value('txtMedIll', illness),
        ],
    }


ANSWER = {
    'answers': [
        answer('txtCoName', 'Example Fabrication LLC'),  # what the deal already says: not listed (D60)
        answer('numTAP', '61'),  # over the live prefill (58)
        answer('chkFBPrior', 'no'),  # a blank: "No"
        answer('drpNumCarr', '2'),
        answer('txtRsnBid', 'renewal increase'),  # one of the options, as listed
        answer('State', 'Florida'),  # the printed name of the code the deal already has (FL)
        answer('txtMcComments', MEDICAL, unsure=True),  # sensitive, and doubted: unticked
    ],
    'rows': [
        {
            'block': 'plans',
            'page': 1,
            'values': [value('txtCurrPlanName', 'BlueOptions 1'), value('numCurrRatePrem', '41250')],
        },
        condition(),
    ],
}


def form_pdf(lines=PAGE):
    return synthetic_files.text_pdf(lines)


def key(raw, label='p1'):
    return ('questionnaire', hashlib.sha256(raw).hexdigest()[:16], label)


def upload(user, deal, raw=None, kind='questionnaire', name='filled questionnaire (synthetic).pdf'):
    return stored(user, deal, name, raw or form_pdf(), kind=kind)


def form_read(user, deal, fake, answer_data=None, *, raw=None, kind='questionnaire', document=None, **recording):
    """Upload the filled form (unless given), record Claude's answer and read it; returns (job, document)."""
    raw = raw or form_pdf()
    document = document or upload(user, deal, raw, kind=kind)
    fake.record(key(raw), ANSWER if answer_data is None else answer_data, **recording)
    job, _ = start_read(user, deal, [document.id], target='questionnaire')
    job.refresh_from_db()
    return job, document


def leaks(text):
    low = str(text).lower()
    return [canary for canary in CANARIES if canary.lower() in low]
