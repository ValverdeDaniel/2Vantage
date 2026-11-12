"""The census reader's prompt and its per-call note (plan.md §10.4, §10.8; C19, D110, D55; slice 51).

One prompt for every census read, built once from the census columns (§4.4): the same bytes for every deal and file, so
it caches. The rules are the old PDF census reader's (`CENSUS_PDF_SYSTEM_PROMPT`, benefits/ai/claude_readers.py at
891f1b3: every person in order, dependents right after their employee, printed values only, never a guess, dates
MM/DD/YYYY, SSNs as printed, low confidence when unsure), restated for the structured answer. The note after the file
says only what the file was filed as and the deal's lines; it never names the file, the client or a person.
"""

from deals import lines as line_vocab
from documents import kinds as document_kinds

from .. import fields

HEAD = """You are an employee-benefits census extractor for an insurance agency. You are shown pages of an employer's \
census: a roster of employees and their dependents (PDF pages, which may be scanned, or a picture). Record every \
person as one entry in `people`, in the order they are printed, in the JSON shape you are given.

How to lay out the answer:
- One entry per person: each employee, then that employee's dependents right after them, then the next employee.
- `dependent` is true for a spouse, child or domestic partner listed under an employee; false for the employee.
- `employee`: for a dependent, the employee it is listed under, first and last name as printed. For an employee, ''.
- `values`: one entry per value printed for the person, each with the census column it fills (`key`, from the list \
below), the `value` exactly as printed, the `page` it is printed on (the file's page number) and `unsure`.

Rules:
- Record only values printed for the person. Never guess, never fill a value from another person or from a total.
- Set `unsure` when a value is ambiguous, partly legible or needed interpretation.
- Dates: MM/DD/YYYY. SSNs: as printed (a masked SSN such as ***-**-1234 stays masked).
- relationship: for a dependent, as printed (Spouse, Child, Domestic Partner...). Leave it out for an employee.
- Coverage tiers (medical_tier, dental_tier, vision_tier): one of EE, ES, EC, FAM, or Waived when the person waived \
the coverage, as printed (Employee Only, Employee + Spouse, Family and the like are fine).
- gender: M or F as printed.
- A plan name printed for the person (Medical Plan, Dental Plan...) goes in the plan column exactly as printed.
- Do not record headings, page headers and footers, column titles, totals, counts or summary rows as people.
- A person printed twice (a page repeated, a roster continued) is recorded once.

Census columns (key = label: what it holds):
"""


def _columns():
    lines = []
    for field in fields.FIELDS:
        help_text = ' '.join(str(field.get('help') or '').split())
        lines.append(f'- {field["key"]} = {field["label"]}' + (f': {help_text}' if help_text else ''))
    return '\n'.join(lines)


PROMPT = HEAD + _columns()


def note(file, context):
    """The per-call note: what the person filed the file as and the deal's lines; never a name (D55)."""
    said = [f'This file was filed as: {document_kinds.label(file.kind) if file.kind else "a census"}.']
    asked = [line_vocab.BY_KEY[key]['label'] for key in context.get('deal_lines', ()) if key in line_vocab.BY_KEY]
    if asked:
        said.append('The deal quotes: ' + ', '.join(asked) + '. Record every column printed, quoted or not.')
    return ' '.join(said)
