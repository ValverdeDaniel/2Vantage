"""What a note's ref names on one deal (plan.md §5.8; L22, L51, L52; old 891f1b3 `review/notes.py` `item_for`,
`_item_of_note`): `resolve(deal, refs)` → {ref: Item}, in a fixed number of queries however many refs (the Intake row,
the people named, the links their answers came through), never one per ref.

An Item: its ref, surface (intake, census, questionnaire, documents), key and person (as a note keeps them,
`rules.refs.note_of`), its words (`label`: "Date of birth — Avery Synthetic", "Their census file", "Renewal — Medical",
"Florida Blue 51+ · Plan 2 · Current plan name"), the request section it belongs to (`section`, as `asks.sections`
names them: a file is the intake's), whether it is `gone` (a person who left the census, a question, row or file the
deal no longer has), whether its page needs the PIN (`pin`: a census value or a questionnaire answer, OQ80), and the
link the client's answer on it came through (`own_link`), whose request a send-back goes back to first.

Staff only: a label names a census person (the ask goes on a page that needs the PIN), never a value.
"""

from collections import namedtuple

from census import fields as census_fields
from census.client_view import title
from census.models import Member
from intake import client_view, form
from intake.models import Intake
from questionnaire import forms as questionnaire_forms
from questionnaire.models import Questionnaire

from ..portal import files_part
from ..rules import asks as ask_rules
from ..rules import refs as ref_rules

Item = namedtuple('Item', 'ref surface key member_id label section gone pin own_link')

BLOCK_LABELS = {
    'contacts': 'Contacts',
    'coverage': 'Current coverage',
    'lines': 'Lines to quote',
    'bor': 'Broker of record signature',
    'files': 'Compliance files',
}
CENSUS_FILE_LABEL = 'Their census file'
WHOLE_FORM = '{form} — the whole form, online'


def _intake(key, client):
    if key.startswith('block:'):
        block = key.removeprefix('block:')
        entry = client.get(key) if key in client_view.BLOCK_SLOTS else None
        return BLOCK_LABELS[block], False, (entry or {}).get('link')
    question = form.BY_KEY.get(key)
    if question is None:
        return key, True, None
    return question['label'], False, (client.get(key) or {}).get('link')


def _census(key, member):
    if member is None or key not in census_fields.BY_KEY or key in census_fields.SSN_KEYS:
        return key, True, None
    label = f'{census_fields.label(key)} — {title(member)}'
    return label, False, ((member.client or {}).get(key) or {}).get('link')


def _document(slot):
    if not ask_rules.slot_valid(slot):
        return slot, True
    return files_part.label(slot), False


def _questionnaire(key, rows):
    """(label, gone, own link) of a whole form (`<form>`) or one of its answers (`<form>:<slot>`)."""
    from . import queue_questionnaire

    form_key, _, slot = key.partition(':')
    name = questionnaire_forms.label(form_key)
    if not slot:
        return WHOLE_FORM.format(form=name), False, None
    row = rows.get(form_key)
    block, _sep, rest = slot.partition('.')
    stored = (row.rows if row else None) or {}
    numbers = {(b, entry['id']): at + 1 for b, listed in stored.items() for at, entry in enumerate(listed)}
    if rest and (block, int(rest.split('.')[0])) not in numbers:
        return f'{name} · {slot}', True, None
    words, _section = queue_questionnaire.label(questionnaire_forms.FORMS[form_key], slot, numbers)
    own = (((row.client if row else None) or {}).get(slot) or {}).get('link')
    return f'{name} · {words}', False, own


def resolve(deal, refs):
    parsed = {ref: ref_rules.note_of(ref) for ref in dict.fromkeys(refs)}
    wanted = {found[2] for found in parsed.values() if found and found[0] == 'census' and found[2] is not None}
    members = {member.id: member for member in Member.objects.filter(deal_id=deal.id, pk__in=wanted)}
    intake = Intake.objects.filter(deal_id=deal.id).only('client').first() if any(
        found and found[0] == 'intake' for found in parsed.values()
    ) else None  # fmt: skip
    client = (intake.client if intake else None) or {}
    forms_named = {found[1].split(':')[0] for found in parsed.values() if found and found[0] == 'questionnaire'}
    rows = {row.form: row for row in Questionnaire.objects.filter(deal_id=deal.id, form__in=forms_named)} if (
        forms_named
    ) else {}  # fmt: skip
    out = {}
    for ref, found in parsed.items():
        if found is None:
            continue
        surface, key, member_id = found
        own = None
        if surface == 'intake':
            label, gone, own = _intake(key, client)
            section = 'intake'
        elif key == ref_rules.CENSUS_FILE:
            label, gone, section = CENSUS_FILE_LABEL, False, 'census'
        elif surface == 'census':
            label, gone, own = _census(key, members.get(member_id))
            section = 'census'
        elif surface == 'questionnaire':
            label, gone, own = _questionnaire(key, rows)
            section = 'questionnaire'
        else:
            (label, gone), section = _document(key), 'intake'  # the checklist's files are the Intake's (D-202)
        pin = (surface == 'census' and key != ref_rules.CENSUS_FILE) or surface == 'questionnaire'
        out[ref] = Item(ref, surface, key, member_id, label, section, gone, pin, own if isinstance(own, int) else None)
    return out
