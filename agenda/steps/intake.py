"""The intake track (I44–I48; plan.md §5.9): the go-to-market gate split into what holds it, one step per blocker,
then "Intake ready — market for quotes", the RFP's cards and the medical questionnaire. Shown while the deal is neither
marketed nor sold; they lead only until quotes are in (OQ90, I.5 bug 3), decided from facts, never from the stage.
Words from old Vantage 891f1b3 `tasks/steps.py` `_intake_steps`. Pure.
"""

from .. import rules
from . import asked
from .base import Steps
from .situation import raw_out

ATTEST = 'attest'
DOCUMENT = 'document'
COVERAGE_INTENT, CENSUS, QUESTIONNAIRE = 'coverage_intent', 'census', 'medical_questionnaire'
# Blocker kinds with their own step here or on another track; any other blocker falls to `finish_intake` (I44).
STEPPED = {'question', 'to_check', 'contacts', 'bor', 'census', 'checklist'}


def add(s: Steps, facts, sit):
    intake = facts.get('intake') or {}
    if not intake:
        return
    if sit.marketed_at is not None:
        s.add('send_rfp', 'Sent to market', tab='rfp', state='done', since=sit.marketed_at)
        return
    if sit.sold:
        return
    lead = not sit.quotes_in
    out = raw_out(sit)
    if intake.get('ready_state') == 'ready':
        s.add('send_rfp', 'Intake ready — market for quotes', lead=lead)
    else:
        _gate(s, facts, intake, out, lead)
    _questionnaire(s, facts, intake, out, lead)
    _rfp(s, facts)


def _gate(s, facts, intake, out, lead):
    blockers = intake.get('blockers') or []
    kinds = {}
    for entry in blockers:
        kinds.setdefault(entry['kind'], []).append(entry)
    warn = {'severity': 'warn', 'lead': lead}
    if kinds.get('question'):
        n = len(kinds['question'])
        s.add('complete_intake', f'Complete intake — {rules.plural(n, "required item")}', **warn)
    items = [row for row in intake.get('items') or [] if row.get('status') == 'missing']
    for row in items:
        if row['key'] == COVERAGE_INTENT:
            s.add('checklist:coverage_intent', 'Confirm the coverage and what we are shopping', **warn)
        elif row.get('satisfy') == ATTEST:
            s.add(f'checklist:{row["key"]}', f'Checklist: {row["label"]}', **warn)
    owed = [row for row in items if row.get('satisfy') == DOCUMENT and row['key'] not in (CENSUS, QUESTIONNAIRE)]
    if owed:
        n = len(owed)
        if asked.files(out, [row.get('kind') or row['key'] for row in owed]):
            s.add('checklist_ask', f'Waiting on the client for {rules.plural(n, "checklist item")}', state='waiting',
                  owner='client', lead=lead)  # fmt: skip
        else:
            s.add('checklist_ask', f'Ask the client for {rules.plural(n, "checklist item")}', **warn)
    pending = ((facts.get('review') or {}).get('pending') or {}).get('intake') or 0
    if pending:
        s.add('review_client_answers', f'Review {rules.plural(pending, "answer")} from the client',
              params={'view': 'queue', 'section': 'intake'}, **warn)  # fmt: skip
    if kinds.get('to_check'):
        s.add('review_flagged_answers', f'Review {rules.plural(len(kinds["to_check"]), "flagged answer")}', **warn)
    if kinds.get('contacts'):
        s.add('add_hr_contact', "Add the client's HR contact", **warn)
    if kinds.get('bor'):
        if asked.bor(out):
            s.add('get_bor', 'Waiting on the client to sign the broker of record letter', state='waiting',
                  owner='client', lead=lead)  # fmt: skip
        else:
            s.add('get_bor', 'Get the broker of record letter signed', **warn)
    rest = [entry for entry in blockers if entry['kind'] not in STEPPED]
    if rest:
        names = ', '.join(entry['label'] for entry in rest[:3])
        s.add('finish_intake', f'Finish intake — {names}', **warn)


def _questionnaire(s, facts, intake, out, lead):
    """The medical questionnaire's own step (I46), composed from intake's checklist row (needed, the form, signed or
    on file), the asks that went out, and the returned files' review state."""
    row = next((item for item in intake.get('items') or [] if item['key'] == QUESTIONNAIRE), None)
    if row is None or row.get('status') == 'waived':
        return
    tab = 'questionnaire' if row.get('form_key') else 'intake'
    pending = ((facts.get('review') or {}).get('pending') or {}).get('questionnaire') or 0
    if pending:  # the client's answers on the portal, waiting for a person (slice 58 fills this count)
        label = f'Review {rules.plural(pending, "questionnaire answer")} from the client'
        queue = {'view': 'queue', 'section': 'questionnaire'}
        s.add('questionnaire', label, tab='review', params=queue, severity='warn', lead=lead)
        return
    files = (facts.get('documents') or {}).get('questionnaire_files') or []
    unchecked = [doc['id'] for doc in files if not doc.get('review_state')]
    if row.get('status') == 'done':
        if row.get('signed'):
            s.add('questionnaire', 'Medical questionnaire signed', tab=tab, state='done')
        elif unchecked:
            s.add('questionnaire', 'Review the returned medical questionnaire', tab='documents',
                  params={'doc': unchecked[0]}, severity='warn', lead=lead, basis=unchecked)  # fmt: skip
        else:
            s.add('questionnaire', 'Medical questionnaire on file', tab=tab, state='done')
        return
    if row.get('status') != 'missing':
        return
    if asked.questionnaire(out):
        s.add('questionnaire', 'Waiting on the client for the medical questionnaire', tab=tab, state='waiting',
              owner='client', lead=lead)  # fmt: skip
    else:
        s.add('questionnaire', 'Send the medical questionnaire', tab=tab, severity='warn', lead=lead)


def _rfp(s, facts):
    """`build_rfp` (I48): the RFP's cards, until the deal is marketed or sold. Never a lead step (the old rule)."""
    rfp = facts.get('rfp') or {}
    total = rfp.get('cards_total') or 0
    if not total:
        return
    done = rfp.get('cards_done') or 0
    if done < total:
        s.add('build_rfp', f'Build the RFP — {done} of {total} cards completed')
    else:
        s.add('build_rfp', 'RFP built', state='done')
