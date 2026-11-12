"""`<questionnaire>`: what a chat on the Questionnaire tab is told about the deal's forms (plan.md §10.6, §10.8; D78,
G106; the old `page_context._questionnaire` at 891f1b3). Never stored, never writes.

Each form the tab shows: which form it is, its progress, whether the officer signed it, and its answers on screen with
where each came from. A medical-history or claimant answer — every slot `forms.sensitive_slots` names, the fix of the
old ANNUAL_SLOTS list — is said only as answered or blank, and a sensitive section's rows only as how many of their
fields are answered (§10.8: no medical answer in a chat). Registered with the reader, behind the PHI-gate switch.
"""

from . import forms, slots, values
from .engine import walk
from .engine.spec import block_fields, get_block, section_fields
from .selectors import context

MAX_CHARS = 12_000
MAX_ROWS = 20
WHERE = {
    'typed': 'typed',
    'client': 'the client’s, waiting for review',
    'stored': 'on the form',
    'prefill': 'filled in from the deal',
}


def _where(stored, live, slot):
    value, where = values.layer(stored, live, slot)
    source = stored.sources.get(slot) or {}
    if where == 'stored' and source.get('origin') == 'ai':
        page = f' p.{source["page"]}' if source.get('page') else ''
        return 'read by Claude from a file' + page + (', to check' if source.get('low') else '')
    return WHERE.get(where, '')


def _value(key, block_key, field, found):
    """An answer as a chat may see it: a sensitive one only as answered."""
    if forms.is_sensitive(key, block_key, field['key']):
        return 'answered'
    return ' '.join(str(found.get(field['key'])).split())


def _form_lines(key, row, facts):
    view = context.form_view(key, row, facts)
    form, stored, live = view.form, view.stored, view.prefill
    what = 'medical questionnaire' if form['kind'] == forms.MEDICAL else 'stop-loss disclosure'
    progress = walk.progress(form, view.view)
    signed = 'signed by the officer, so read-only' if row is not None and row.locked else 'not signed'
    lines = [
        f'Form {key}: the {what} "{form["title"]}" ({form["carrier"]}).',
        f'Progress: {progress["filled"]} of {progress["total"]} required answers on screen ({progress["pct"]}%); '
        f'{signed}.',
    ]
    if not context.started(row):
        lines.append('Not started: no answer is stored yet; what shows is filled in from the deal.')
    scalars, by_block = walk.visible_values(form, view.view)
    lines.append('Answers — question (key) = answer [where it came from]:')
    for field in section_fields(form):
        value = scalars.get(field['key'])
        if value in (None, '') or field.get('auto'):
            continue
        shown = _value(key, '', field, scalars)
        where = _where(stored, live, field['key'])
        lines.append(f'- {field.get("label") or field["key"]} ({field["key"]}) = {shown} [{where}]')
    for block_key, rows in by_block.items():
        if not rows:
            continue
        block = get_block(form, block_key)
        lines.append(f'Section "{block["label"]}": {len(rows)} row(s)')
        fields = [field for field in block_fields(form, block_key) if not field.get('auto')]
        for number, (row_id, row_values) in enumerate(rows[:MAX_ROWS], start=1):
            filled = [field for field in fields if str(row_values.get(field['key']) or '').strip()]
            if forms.is_sensitive(key, block_key, None):
                lines.append(f'- row {number}: answered ({len(filled)} of {len(fields)} fields), values not shown')
                continue
            parts = [
                f'{field.get("label") or field["key"]}={_value(key, block_key, field, row_values)}'
                f' [{_where(stored, live, slots.key(block_key, row_id, field["key"]))}]'
                for field in filled
            ]
            lines.append(f'- row {number}: ' + (', '.join(parts) or '(blank)'))
    return lines


def provide(deal, page):
    """<questionnaire> on the Questionnaire tab ('' elsewhere)."""
    if (page or {}).get('tab') != 'questionnaire':
        return ''
    ctx = context.deal_context(deal)
    keys = context.chips(ctx)
    if not keys:
        return '<questionnaire>\nThis deal has no in-app questionnaire form.\n</questionnaire>'
    facts = context.prefill_facts(deal)
    lines = []
    for key in keys:
        lines.extend(_form_lines(key, ctx.stored.get(key), facts))
    text = '\n'.join(lines)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS].rsplit('\n', 1)[0] + f'\n(cut at {MAX_CHARS:,} characters)'
    return f'<questionnaire>\n{text}\n</questionnaire>'
