"""The go-to-market gate's words (plan.md §5.2; B25–B27, B31). A data module: each checklist item's label and detail,
the size tiers' labels and the census's address word, as old Vantage 891f1b3 `benefits/market/marketing_checklist.py`
wrote them (from the team's "Marketing Checklist.docx"), and the compliance uploads' list. The rules that pick among
them are `intake/checklist.py`.
"""

# Size tiers by enrolled headcount (B25), high to low.
GE100, MID, SMALL, MICRO = 'ge100', 'mid', 'small', 'micro'
TIER_LABELS = {
    GE100: '100+ enrolled',
    MID: '51–99 enrolled',
    SMALL: '11–50 enrolled',
    MICRO: 'Under 10 enrolled',
}
# The census's address column by tier: home addresses for the larger bands, ZIP codes below 51 (B25).
GEO = {GE100: 'home address', MID: 'home address', SMALL: 'ZIP code', MICRO: 'ZIP code'}

COVERAGE_INTENT_LABEL = 'Confirm current coverage & what we’re shopping'
COVERAGE_INTENT_DETAIL = (
    'Which lines are in force, which we’re marketing this year, and which go on the proposal without going out for '
    'RFP. This decides the rest of the list — confirm it first.'
)
COVERAGE_INTENT_STALE = (
    'Coverage or the shopping list changed since this was confirmed — take another look and confirm again.'
)

CENSUS_LABEL = 'Member-level census'
CENSUS_DETAIL = 'Employees + dependents — gender, DOB, {geo}, current elections.'

COBRA_LABEL = 'COBRA participants'
COBRA_DETAIL = (
    'Anyone on COBRA through the TPA belongs on the member-level census — they are quoted with the group. Validated '
    'on the Census tab, even when there are none.'
)

SALARY_LABEL = 'Salaries & occupation'
SALARY_DETAIL = 'Required because a life or disability line is being quoted.'

# The medical questionnaire's words follow the tier (old `_questionnaire_copy`).
QUESTIONNAIRE = {
    GE100: (
        'Medical questionnaire — completed & signed',
        'Florida Blue, Humana. Per HIPAA, enter "no"/"N/A" rather than employee medical detail where applicable.',
    ),
    SMALL: (
        'Group medical questionnaire — completed & signed',
        'AvMed GHT, FL Blue Balanced Funded, and Trustmark (25+ enrolled).',
    ),
    MICRO: (
        'Individual medical questionnaires — completed & signed',
        'Census & questionnaires must match. UHC IMQ works for UHC/Aetna/AvMed; IMQs not required for Aetna/AvMed at '
        '5+ enrolled coming off a level-funded plan.',
    ),
}
QUESTIONNAIRE[MID] = QUESTIONNAIRE[GE100]

STOP_LOSS_LABEL = 'Stop-loss disclosure — completed & signed'
STOP_LOSS_DETAIL = (
    'Universal SIIA disclosure of known risks (Oct 2015) — used beside the medical questionnaire for level/self-funded '
    'and large groups. The client lists individuals (or checks "no risks") and signs.'
)

RENEWAL_LABEL = 'Current benefits renewal & rates'
RENEWAL_DETAIL = 'The incumbent renewal letter with current rates.'
INVOICE_LABEL = 'Current invoice(s)'
INVOICE_DETAIL = 'A recent carrier bill/invoice for the current plan(s).'
# Why the renewal and invoice read "Not needed" when nobody waived them (D-183).
NOT_IN_FORCE_DETAIL = (
    'Nothing is in force today, so there is no current renewal or invoice. If they do have coverage, tick In force on '
    'the coverage card.'
)
NOT_SHOPPED_DETAIL = (
    'No line is both in force and being shopped, so no current renewal or invoice is needed. If one is being shopped, '
    'say so on the coverage card.'
)

CLAIMS_LABEL = 'Claims experience'
CLAIMS_DETAIL_LARGE = 'Last 2 years of claims (required at 100+ enrolled).'
CLAIMS_DETAIL_FUNDED = 'Required from the current carrier for level/self-funded groups.'

# Compliance & authorizations (B31): the document kinds the card lists for upload, in the old card's words
# (891f1b3 `IntakeTab.jsx` COMPLIANCE_TYPES; old `claims_exp` is 2V's `claims`).
COMPLIANCE = [
    ('bor', 'Broker of Record letter'),
    ('carrier_auth', 'Carrier authorization'),
    ('claims', 'Claims experience report'),
    ('form_5500', 'Most recent 5500'),
    ('plan_doc', 'Plan / wrap documents'),
]
