"""The receipt a link shows once its person submitted (plan.md §7.14, §8.20; L99, the old roadmap's N1; slice 59):
what went through this link, by section, as labels and counts, with the time of its last Submit.

`receipt(link, deal) -> {at, sections: [{key, title, lines: [str]}]}`, or None until the link was submitted. The
sections follow the page: the company intake (how many answers, the contacts, coverage and lines to quote, the BOR
signature), each questionnaire (its answers, signed), the employees (details given, people added) and the files, by
the slot each answered ("Employee census file", "Current invoice — Medical — 2 files"). Only this link's own: a
colleague's answers and another link's files never show (B22; a blank link sees no more than its own, L66).
Allowlisted like the rest of the page (L108): labels and counts, never a value and never a file's name (a census file
is often named after its people: file names are PHI, §3.8; the submit answer carries it), and nothing about what we
did with it (approved, read: L109). Four reads, only for a submitted link.
"""

from census.models import PERSON, Member
from documents.models import Document
from intake.client_view import BLOCK_SLOTS
from intake.models import Intake
from questionnaire import forms as questionnaire_forms
from questionnaire.models import Questionnaire

from . import files_part, words
from .asked import PAPER


def _plural(count, one, many=None):
    return f'{count} {one if count == 1 else many or one + "s"}'


def _mine(client, link_id):
    """The slots of an owner's `client` JSON this link answered (whatever became of the answer since)."""
    return [slot for slot, entry in (client or {}).items() if isinstance(entry, dict) and entry.get('link') == link_id]


def _intake(deal, link_id):
    row = Intake.objects.filter(deal=deal).only('client', 'bor_via').first()
    if row is None:
        return []
    mine = set(_mine(row.client, link_id))
    answers = len([slot for slot in mine if slot not in BLOCK_SLOTS])
    lines = [_plural(answers, 'answer')] if answers else []
    lines += [words.RECEIPT_BLOCKS[slot] for slot in BLOCK_SLOTS if slot in mine]
    if (row.bor_via or {}).get('link') == link_id:
        lines.append(words.RECEIPT_BOR)
    return lines


def _forms(deal, link_id):
    lines = []
    for row in Questionnaire.objects.filter(deal=deal).only('form', 'client', 'officer_link').order_by('id'):
        answered, signed = len(_mine(row.client, link_id)), row.officer_link == link_id
        if answered or signed:
            parts = ([_plural(answered, 'answer')] if answered else []) + (['signed'] if signed else [])
            lines.append(f'{questionnaire_forms.label(row.form)}: {" · ".join(parts)}')
    return lines


def _people(deal, link_id):
    details = added = 0
    rows = Member.all_objects.filter(deal=deal).exclude(client={}).values_list('client', 'added_by_link')
    for client, by_link in rows:
        added += by_link == link_id
        details += len([column for column in _mine(client, link_id) if column != PERSON])
    lines = [_plural(details, 'detail')] if details else []
    return lines + ([f'{_plural(added, "person", "people")} added'] if added else [])


def _file_label(slot):
    if slot == files_part.CENSUS_SLOT:
        return words.RAIL['census']
    if slot.startswith(PAPER):
        return f'{questionnaire_forms.label(slot[len(PAPER) :])} — {words.RECEIPT_PAPER}'
    return files_part.label(slot)


def _files(link_id):
    counted = {}  # by slot, in the order the files came (by id: the clock can step back)
    for slot in Document.objects.filter(link_id=link_id, source='client').order_by('id').values_list('slot', flat=True):
        counted[slot] = counted.get(slot, 0) + 1
    return [_file_label(slot) + (f' — {count} files' if count > 1 else '') for slot, count in counted.items()]


def receipt(link, deal):
    if link.submitted_at is None:
        return None
    found = (
        ('intake', _intake(deal, link.id)),
        ('questionnaires', _forms(deal, link.id)),
        ('people', _people(deal, link.id)),
        ('files', _files(link.id)),
    )
    sections = [{'key': key, 'title': words.RECEIPT[key], 'lines': lines} for key, lines in found if lines]
    return {'at': link.submitted_at.isoformat(), 'sections': sections}
