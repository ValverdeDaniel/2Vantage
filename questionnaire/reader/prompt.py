"""The questionnaire reader's prompt and its per-call note (plan.md §10.4; D55, G99; slice 52).

One prompt for every read of a filled form, built once from the three forms' specs (G1): the same bytes for every
deal, form and file, so it caches. The rules are the old reader's (`QFORM_SYSTEM_PROMPT`, benefits/ai/claude_readers.py
at 891f1b3: copy answers exactly as written, never infer or invent medical or personal information, leave unanswered
questions out, one listed option for a picker, digits for counts and amounts; each answer's own page, D-152; Claude's
doubt, D-145), restated for the structured answer. The note after the file says what it was filed as and which of the
deal's forms it fills — never the file's name or the client's (D55).
"""

from documents import kinds as document_kinds

from .. import forms
from ..engine.options import alias, flat_options
from ..engine.spec import block_keys, get_block

HEAD = """You transcribe a filled carrier underwriting form — a group medical questionnaire or a stop-loss disclosure \
— into structured data. Copy the answers exactly as written: never infer, estimate or invent medical or personal \
information, and leave unanswered questions out entirely. The file is PDF pages (typed, stamped or handwritten, maybe \
scanned) or a picture of the form.

The note after the file names the form it fills. Record, in the JSON shape you are given:
1. `answers`: each of that form's questions the file answers: its `key` from the form's list below, the answer as \
written, the `page` it is printed on (the file's page number; 1 for a picture) and `unsure`.
2. `rows`: each filled row of the form's repeating sections, in printed order: its `block`, the `page` it is printed \
on, and its `values` (each a `key` from that section's list, the value as written, and `unsure`). Leave out a row \
with nothing filled in, and the row numbers the form prints.

Rules:
- Only what was filled in. A question left blank is left out; so is a page that is not part of the form (a cover \
letter, instructions, a blank page).
- Set `unsure` when handwriting is unclear, a box is smudged, two boxes are ticked or the answer needed interpretation.
- Yes/No questions: Yes or No (a ticked box is the answer it sits by). A question with options: exactly one of its \
options as listed.
- Dates: MM/DD/YYYY. Counts, amounts and percents: digits only, no $, % or commas.
- Use only the keys of the form the note names; never put a repeating section's field in `answers`.

Forms (key = question [type; what to write]):
"""

TYPES = {
    'text': 'text',
    'date': 'date, MM/DD/YYYY',
    'number': 'number, digits only',
    'money': 'amount, digits only',
    'percent': 'percent, digits only',
    'choice': 'choice',
    'yesno': 'Yes or No',
}
TABLE_WORDS = {'conditions_by_category': 'conditions', 'details_by_condition': 'details'}


def _picker(form, field):
    """What a picker takes, in words: its options, or where its options are listed."""
    if field.get('depends_on'):
        parent = next(f for f in _fields_of(form) if f['key'] == field['depends_on'])
        words = TABLE_WORDS.get(field.get('options_from'), 'options')
        return f'; one of the {words} listed under its {parent["label"]} below'
    if field.get('option_mode') == 'code':
        return '; the 4-digit SIC code, digits only'
    if field.get('option_mode') == 'description':
        return '; the SIC industry description as printed'
    options = list(field.get('options') or []) or flat_options(form, field)
    shown = ', '.join(map(str, options))
    printed = field.get('display_map') or {}
    if printed and all(len(str(value)) <= 3 for value in printed.values()):
        shown += f' (the paper prints {", ".join(printed.values())})'
    elif printed:
        shown += ' (the paper may print the full name)'
    return f'; one of: {shown}'


def _fields_of(form):
    out = [field for section in form['sections'] for field in section.get('fields') or []]
    for key in block_keys(form):
        out.extend(get_block(form, key)['fields'])
    return out


def _line(form, field, indent='- '):
    kind = field.get('type', 'text')
    words = TYPES.get(kind, kind) + (_picker(form, field) if kind == 'choice' else '')
    label = ' '.join(str(field.get('label') or field['key']).split())
    return f'{indent}{field["key"]} = {label} [{words}]'


def _tables(form):
    """The dependent pickers' options, in the option labels the pickers offer (through the form's aliases)."""
    tables = form.get('tables') or {}
    lines = []
    for field in _fields_of(form):
        if not field.get('depends_on'):
            continue
        parent = next(f for f in _fields_of(form) if f['key'] == field['depends_on'])
        table = tables.get(field['options_from']) or {}
        if parent.get('depends_on'):  # a picker under a picker: its parents are every option of the level above
            above = tables.get(parent['options_from']) or {}
            parents = list(dict.fromkeys(option for options in above.values() for option in options))
        else:
            parents = list(parent.get('options') or []) or flat_options(form, parent)
        lines.append(f'{TABLE_WORDS.get(field["options_from"], "Options").capitalize()} by {parent["label"]}:')
        for value in parents:
            options = table.get(alias(form, field.get('alias', ''), value)) or []
            if options:
                lines.append(f'  {value}: {"; ".join(options)}')
    return lines


def _form(form):
    lines = [f'## {form["key"]}: {form["title"]} ({forms.label(form["key"])})', 'Questions:']
    for section in form['sections']:
        lines.extend(_line(form, field) for field in section.get('fields') or [] if not field.get('auto'))
    if block_keys(form):
        lines.append('Repeating sections (block: label, rows):')
    for key in block_keys(form):
        block = get_block(form, key)
        lines.append(f'- {key}: {block["label"]}, up to {block["max_rows"]} rows')
        lines.extend(_line(form, field, '  - ') for field in block['fields'] if not field.get('auto'))
    lines.extend(_tables(form))
    return '\n'.join(lines)


PROMPT = HEAD + '\n\n'.join(_form(form) for form in forms.FORMS.values())


def note(file, context):
    """The per-call note: what the person filed the file as and the deal's form it fills; never a name (D55)."""
    from . import which

    filed = document_kinds.label(file.kind) if file.kind else 'a filled form'
    document = getattr(file, 'document', None)
    key = which.forms_of(document.deal_id, [file]).get(file.id) if document is not None else ''
    if not key:
        return f'This file was filed as: {filed}. Record its answers with the keys of the form it is.'
    return f'This file was filed as: {filed}. It fills the deal\'s {forms.label(key)} form: use the keys of "{key}".'
