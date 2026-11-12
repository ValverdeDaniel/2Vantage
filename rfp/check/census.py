"""One carrier format's problems (plan.md §9.8; K74; old Vantage 891f1b3 `export_check.census_problems`). Reads the
format's rows from the one builder the download runs (`rfp.formats.rows`), so the check says what the file holds.

- The builder's own warnings, each with its code: a translation note (with the people it concerns, on our own screen
  only), a blank tier counted once per employee (bug 17), the cap's one truthful line (bug 16; OQ61), members outside
  the lower 48, the required cells left blank; each sends the person to the format's lens.
- Validation errors still open on the census.
- The carrier's group tab (UHC's Group Info): the facts we store that are blank on this deal.
- Angle's CSV: how many values start like a formula and go out behind an apostrophe (K74, K107).
"""

from documents.xlsx_safe import csv_text

from .. import printed
from ..formats import lens, rows, translate
from .problems import plural, problem

# Aetna's AFA UW / FI UW selector stays blank on purpose when both fundings are asked, for the reader to choose.
BLANK_ON_PURPOSE = frozenset({'rfp.aetna_underwriting'})
CODES = (
    ('room for', 'overflow'),
    ('on a line you are quoting', 'blank_tier'),
    ('required cell', 'required_blank'),
    ('out of area', 'out_of_area'),
)


def _code(text):
    return next((code for opening, code in CODES if opening in text), 'file')


def _formula_like(fmt, built):
    count = 0
    for values in built.rows:
        for column, text in zip(fmt['columns'], values, strict=True):
            typed = translate.typed(column, text)
            if isinstance(typed, str) and typed and csv_text(typed) != typed:
                count += 1
    return count


def _group_blanks(ctx, fmt):
    if not fmt.get('group_info'):
        return []
    facts = printed.form_facts(ctx)
    blank = [
        (entry.get('label') or entry['cell']).lstrip('*')
        for entry in fmt['group_info']
        if facts.get(entry['source']) in ('', None) and entry['source'] not in BLANK_ON_PURPOSE
    ]
    blank = list(dict.fromkeys(blank))
    if not blank:
        return []
    n = len(blank)
    shown = ', '.join(blank[:6]) + ('…' if n > 6 else '')
    text = f'{n} {plural(n, "fact", "facts")} on their group tab {plural(n, "is", "are")} blank: {shown}.'
    return [problem('group_blank', text, n, fix={'tab': 'intake'})]


def problems(ctx, fmt, lens_key, kind='xlsx'):
    built = rows.build(fmt, ctx.people, ctx.lines, ctx.deal.effective_date)
    names = {person['id']: lens.person_name(person) for person in built.people}
    notes = {note['text']: note for note in built.notes}
    fix = {'tab': 'census', 'lens': lens_key}
    out = []
    for text in built.warnings:
        note = notes.get(text)
        if note:
            people = [names.get(pk, 'Someone') for pk in note['row_ids']]
            out.append(problem(note['code'], text, note['count'], fix, people=people))
        elif kind == 'csv' and _code(text) == 'overflow':
            continue  # the CSV carries everyone
        else:
            out.append(problem(_code(text), text, fix=fix))
    errors = ctx.census['errors']
    if errors:
        text = f'{errors} validation {plural(errors, "error remains", "errors remain")} in the census — fix before ' \
            'sending to the carrier.'  # fmt: skip
        out.append(problem('validation', text, errors, fix={'tab': 'census'}))
    out += _group_blanks(ctx, fmt)
    if kind == 'csv':
        n = _formula_like(fmt, built)
        if n:
            text = (
                f'{n} census {plural(n, "value starts", "values start")} with =, +, - or @, so the CSV carries '
                f'{plural(n, "it", "them")} as text behind a leading apostrophe.'
            )
            out.append(problem('csv_formula', text, n, fix=fix))
    return out
