"""How a request card names what a request asks (L8): a phrase each, the old `_link_asks` words (891f1b3
serializers/overview.py), e.g. "The census gaps · The census file · Intake gaps". Pure: vocabularies only."""

from deals import lines
from documents import kinds
from questionnaire import forms as questionnaire_forms

INTAKE_WORDS = {'all': 'Intake form', 'missing': 'Intake gaps', 'required': 'Intake needed to market'}
BLOCK_WORDS = {
    'contacts': 'Contacts',
    'coverage': 'Coverage in force',
    'lines': 'Lines to quote',
    'bor': 'Broker of record',
    'files': 'Compliance files',
}
CENSUS_WORDS = {'missing': 'The census gaps', 'blank': 'Every blank in the census', 'all': 'The whole census'}


def _plural(count, noun):
    return f'{count} {noun}{"" if count == 1 else "s"}'


def _intake_words(intake):
    out = []
    scope = intake.get('scope')
    if scope == 'selected':
        out.append(_plural(len(intake.get('keys') or []), 'intake question'))
    elif scope:
        out.append(INTAKE_WORDS[scope])
    out += [BLOCK_WORDS[block] for block in intake.get('blocks') or [] if block in BLOCK_WORDS]
    return out


def _census_words(census):
    out = []
    scope = census.get('scope', 'none')
    if scope == 'selected':
        out.append(_plural(len(census.get('cells') or []), 'census value'))
    elif scope in CENSUS_WORDS:
        columns = census.get('columns') or []
        out.append(_plural(len(columns), 'census column') if columns else CENSUS_WORDS[scope])
    if census.get('file'):
        out.append('The census file')
    return out


def _slot_words(slot):
    kind, _, line = slot.partition('@')
    return f'{kinds.label(kind)} · {lines.label(line)}' if line else kinds.label(kind)


def words(asks):
    """What a request asks, a phrase each, in the request card's order: census, intake, forms, then files."""
    asks = asks or {}
    out = _census_words(asks.get('census') or {}) + _intake_words(asks.get('intake') or {})
    for form in asks.get('questionnaires') or []:
        name = questionnaire_forms.label(form['form']) or 'Questionnaire'
        out.append(f'{name} (upload)' if form.get('mode') == 'upload' else name)
    documents = asks.get('documents') or {}
    out += [_slot_words(slot) for slot in documents.get('slots') or []]
    if documents.get('missing'):
        out.append('Any missing documents')
    return out
