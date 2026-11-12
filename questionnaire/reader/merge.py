"""Joining a questionnaire read's answers (plan.md §10.4; G99; the old `_merge_qform` at 891f1b3).

Each range's answer goes to the form its file fills (`which`), files in upload order and each file's pages in order:
- an answer: the first reading wins; a different later reading leaves the first, doubted, so it arrives unticked;
- a row of a repeating section is appended in printed order, up to the section's maximum; a row past it is counted,
  never silently lost (the old L-8);
- an answer or row keeps the page Claude says it is printed on when that page is in its range, else the range's
  first page (D-152);
- a key that is not one of its form's questions, or a section's field given as a question, is counted and left out.
No value is cleaned here: `clean.clean` does it against the form (`changes.build_changes`).
"""

from .. import forms
from ..engine.spec import block_fields, get_block, section_fields
from . import which

TWICE = 'Read two ways in this file; the first reading is kept.'
UNSURE = 'Claude was not sure of this answer.'


def empty():
    return {'documents': [], 'answers': {}, 'rows': {}, 'dropped': {}, 'unknown': 0, 'twice': 0}


def _text(raw):
    return '' if raw is None else ' '.join(str(raw).split())


def _page(raw, first, last):
    return raw if isinstance(raw, int) and not isinstance(raw, bool) and first <= raw <= last else first


def _answers(form, target, data, doc, first, last):
    keys = {field['key'] for field in section_fields(form) if not field.get('auto')}
    for answer in data.get('answers') or []:
        if not isinstance(answer, dict):
            continue
        key, value = answer.get('key'), _text(answer.get('value'))
        if key not in keys:
            target['unknown'] += 1
            continue
        if not value:
            continue
        held = target['answers'].get(key)
        if held is None:
            low = UNSURE if answer.get('unsure') else ''
            page = _page(answer.get('page'), first, last)
            target['answers'][key] = {'value': value, 'page': page, 'low': low, 'doc': doc}
        elif held['value'] != value:
            held['low'] = TWICE
            target['twice'] += 1


def _rows(form, target, data, doc, first, last):
    for row in data.get('rows') or []:
        if not isinstance(row, dict) or get_block(form, row.get('block')) is None:
            target['unknown'] += 1
            continue
        block = row['block']
        keys = {field['key'] for field in block_fields(form, block) if not field.get('auto')}
        values, low = {}, []
        for entry in row.get('values') or []:
            if not isinstance(entry, dict):
                continue
            key, value = entry.get('key'), _text(entry.get('value'))
            if key not in keys:
                target['unknown'] += 1
                continue
            if value and key not in values:
                values[key] = value
                if entry.get('unsure'):
                    low.append(key)
        if not values:
            continue
        listed = target['rows'].setdefault(block, [])
        if len(listed) >= get_block(form, block)['max_rows']:
            target['dropped'][block] = target['dropped'].get(block, 0) + 1
            continue
        listed.append({'values': values, 'page': _page(row.get('page'), first, last), 'low': low, 'doc': doc})


def merge(parts, files):
    """{form key: {documents, answers {key: {value, page, low, doc}}, rows {block: [{values, page, low, doc}]},
    dropped {block: n}, unknown, twice}} for the parts [(file, range, data)] of one read."""
    deal_id = next((file.document.deal_id for file in files if getattr(file, 'document', None) is not None), None)
    form_of = which.forms_of(deal_id, files) if deal_id else {}
    order = {file.id: file.order for file in files}
    out = {}
    ranked = sorted(parts, key=lambda found: (order.get(found[0].id, 0), min(found[1].pages or (0,))))
    for file, part, data in ranked:
        form = forms.get_form(form_of.get(file.id))
        if form is None or not isinstance(data, dict):
            continue
        target = out.setdefault(form['key'], empty())
        if file.id not in target['documents']:
            target['documents'].append(file.id)
        pages = tuple(part.pages or ()) or (1,)
        _answers(form, target, data, file.id, min(pages), max(pages))
        _rows(form, target, data, file.id, min(pages), max(pages))
    return out
