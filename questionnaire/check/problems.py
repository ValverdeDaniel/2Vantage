"""What is wrong with one filled form before it leaves (G64). Pure: each problem is `{code, text, count, fix}`.

The codes, worst first, as old Vantage's export check had them (891f1b3 `pipeline/export_check.questionnaire_problems`
and `questionnaires/check.py`):
- `questionnaire_empty`: nobody has started the form (alone: nothing else is worth saying);
- `questionnaire_incomplete`: required answers on screen still blank; `unsigned`: the officer has not signed;
- `claimant_name`: a de-identified field (the SIIA Risk Identifier) that looks like a full name — named by row;
- what the PDF cannot print (`stamp_place.clip_report`, `acroform.unprinted`): `clipped`, `on_attachment`,
  `rows_on_attachment`, `not_printed`; hidden rows are worked out live, never from a stored row number (B2);
- until the officer signs, what waits on a person: `questionnaire_ai_open` (values Claude doubted, not yet looked at)
  and `questionnaire_client_waiting` (the client's answers nobody reviewed).
Texts name fields by label and rows by number, never an answer: a questionnaire's answers are medical history.
"Still typing" and the last read's findings wait for the review app and the reader (slices 53, 52).
"""

import re

from ..engine.spec import block_fields, block_keys, field_spec, get_block, section_fields
from ..pdf import acroform, stamp_place

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def plural(n, one, many):
    return one if n == 1 else many


def problem(code, text, count=0, fix=None):
    return {'code': code, 'text': text, 'count': count, 'fix': fix}


def looks_like_a_name(value):
    """'Jordan Reyes' yes; 'J.R.', 'JR', 'M-10442', 'EE 3' no: two or more words of letters, each at least two long,
    one at least three, and no digit. A warning's rule, not a classifier."""
    raw = str(value or '').strip()
    if not raw or any(ch.isdigit() for ch in raw):
        return False
    words = _WORD.findall(raw)
    return len(words) >= 2 and all(len(w) >= 2 for w in words) and any(len(w) >= 3 for w in words)


def label(form, block, number, key):
    """'Plan 2 · Plan Name/Description', 'Risk 3', or a scalar's own label."""
    name = (field_spec(form, block, key) or {}).get('label') or key
    if not block:
        return name
    spec = get_block(form, block) or {}
    row = f'{spec.get("row_label") or spec.get("label") or block} {number}'
    return f'{row} · {name}' if key else row


def claimants(form, found, fix):
    named = []
    for block in block_keys(form):
        keys = [f['key'] for f in block_fields(form, block) if f.get('deidentified')]
        if not keys:
            continue
        for number, vals in found.rows.get(block) or []:
            if any(looks_like_a_name(vals.get(key)) for key in keys):
                named.append(label(form, block, number, ''))
    for field in section_fields(form):
        if field.get('deidentified') and looks_like_a_name(found.scalars.get(field['key'])):
            named.append(label(form, '', 0, field['key']))
    if not named:
        return []
    n = len(named)
    text = (
        f'{n} claimant {plural(n, "identifier looks", "identifiers look")} like a full name ({", ".join(named)}): '
        'the form asks for initials or a member ID, never a name.'
    )
    return [problem('claimant_name', text, n, fix)]


def _block_label(form, block):
    return (get_block(form, block) or {}).get('label', block)


def output(form, found, layout, fix):
    """What the carrier's pages cannot print, said so nobody is surprised by the extra page."""
    out, dropped, more = [], {}, {}
    if form.get('acroform'):
        report = acroform.unprinted(form, form['acroform'], found)
        attached = [label(form, '', 0, key) for key in report['attached']]
        dropped = report['dropped']
    elif layout is not None:
        report = stamp_place.clip_report(form, layout, found)
        attached = [label(form, *where) for where in report['attached']]
        more = report['rows']
        if report['clipped']:
            n = len(report['clipped'])
            names = ', '.join(label(form, *where) for where in report['clipped'])
            text = (
                f'{n} {plural(n, "answer is", "answers are")} too long for {plural(n, "its box", "their boxes")} '
                f"on the carrier's page and will be cut short ({names})."
            )
            out.append(problem('clipped', text, n, fix))
    else:
        return []
    if attached:
        n = len(attached)
        text = (
            f"{n} {plural(n, 'answer prints', 'answers print')} on an attachment page after the carrier's form, "
            f'which has no room for {plural(n, "it", "them")} ({", ".join(attached)}).'
        )
        out.append(problem('on_attachment', text, n, fix))
    for block, n in sorted(more.items()):
        text = (
            f'{n} more {_block_label(form, block)} {plural(n, "row prints", "rows print")} on an attachment page: '
            "the carrier's form shows one."
        )
        out.append(problem('rows_on_attachment', text, n, fix))
    for block, n in sorted(dropped.items()):
        text = (
            f"{n} {_block_label(form, block)} {plural(n, 'row has', 'rows have')} no row on the carrier's form "
            'and will not print.'
        )
        out.append(problem('not_printed', text, n, fix))
    return out


def problems(form, found, layout, *, started, signed, blank, open_reads, waiting):
    """[problem] for one form, worst first. `blank`: required answers on screen still blank; `open_reads`: values
    Claude doubted that nobody looked at; `waiting`: the client's answers nobody reviewed."""
    fix = {'tab': 'questionnaire', 'form': form['key']}
    review = {**fix, 'view': 'review'}
    title = form['title']
    if not started:
        return [problem('questionnaire_empty', f'{title} has not been started.', 0, fix)]
    out = []
    if blank:
        words = f'{blank} required {plural(blank, "answer", "answers")} on {title} {plural(blank, "is", "are")}'
        out.append(problem('questionnaire_incomplete', f'{words} still blank.', blank, fix))
    if not signed:
        out.append(problem('unsigned', f'{title} is not signed by the officer yet.', 0, fix))
    out += claimants(form, found, review)
    out += output(form, found, layout, fix)
    if not signed and open_reads:
        text = (
            f'{open_reads} {plural(open_reads, "answer", "answers")} the AI read off the filled form '
            f'{plural(open_reads, "has", "have")} not been checked by a person.'
        )
        out.append(problem('questionnaire_ai_open', text, open_reads, review))
    if not signed and waiting:
        text = (
            f'{waiting} {plural(waiting, "answer", "answers")} the client sent {plural(waiting, "is", "are")} '
            'not reviewed yet.'
        )
        out.append(problem('questionnaire_client_waiting', text, waiting, review))
    return out
