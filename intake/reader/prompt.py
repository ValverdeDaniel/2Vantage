"""The intake reader's prompt and its per-call note (plan.md §10.4; B40, D55, D112; slice 51).

One prompt for every intake read, built once from the intake form (§4.5): the same bytes for every deal and file, so
it caches. The rules are the old intake reader's (`INTAKE_SYSTEM_PROMPT`, benefits/ai/claude_readers.py at 891f1b3:
the three parts, printed values only, never a guess, low confidence when unsure, FEIN XX-XXXXXXX, dates MM/DD/YYYY,
funding from claims or stop-loss language, empty lists for a document with no intake data), restated for the
structured answer. The note after the file says only what it was filed as; never its name or the client's.
"""

from deals import contacts as contact_vocab
from deals import lines as line_vocab
from documents import kinds as document_kinds

from .. import form

HEAD = """You are an employee-benefits intake data extractor for an insurance agency. You are shown a document an \
employer already has: a current benefit summary, a carrier invoice, a renewal or rate letter, a plan document, a \
Form 5500, or a completed intake form (PDF pages, which may be scanned, a spreadsheet as a grid of cells, or a \
picture). Pull the group's intake details so the employer does not have to type them again.

Record three things, in the JSON shape you are given:
1. `fields`: each intake question below the document answers, with its value, its `page` (the file's page number; 0 \
in a spreadsheet or a picture), its `cell` in a spreadsheet ("Sheet1!B4"; '' otherwise) and `unsure`.
2. `coverage`: the coverage the group has in force today, one entry per line of coverage, with the carrier, the \
funding and the renewal date when printed ('' when not), and its page.
3. `contacts`: named benefits, HR or decision-making contacts of the group, with title, email and phone as printed \
('' when not) and their role from the list when the document says it ('' otherwise).

Rules:
- Record only values printed in the document. Never guess, never infer a value that is not printed.
- Set `unsure` when a value is ambiguous, partly legible or needed interpretation.
- FEIN: XX-XXXXXXX. Dates: MM/DD/YYYY. Numbers, amounts and percents: digits only (no %, $ or commas).
- Yes/No questions: Yes or No. A question with options: one of its options, as listed.
- funding is one of: {funding}. A plan with claims data or stop-loss is self_funded or level_funded; otherwise \
fully_insured. '' when the document does not say.
- Never record a plan member, a patient or a claimant as a contact, and never record anyone's medical details.
- A document with no intake data (a marketing flyer, a blank form) gets empty lists.

Contact roles: {roles}.
Lines of coverage: {lines}.

Intake questions (key = label [type; options]: what it asks):
"""


def _questions():
    lines = []
    for question in form.QUESTIONS:
        options = question.get('options') or []
        shown = f'; one of: {", ".join(map(str, options))}' if options else ''
        help_text = ' '.join(str(question.get('help') or '').split())
        lines.append(f'- {question["key"]} = {question["label"]} [{question["type"]}{shown}]: {help_text}')
    return '\n'.join(lines)


PROMPT = (
    HEAD.format(
        funding=', '.join(key for key, _label in line_vocab.FUNDING),
        roles=', '.join(f'{key} ({label})' for key, label in contact_vocab.ROLES),
        lines=', '.join(f'{line["key"]} ({line["label"]})' for line in line_vocab.LINES),
    )
    + _questions()
)


def note(file, context):
    """The per-call note: what the person filed the file as; never a name (D55)."""
    return f'This file was filed as: {document_kinds.label(file.kind) if file.kind else "a company document"}.'
