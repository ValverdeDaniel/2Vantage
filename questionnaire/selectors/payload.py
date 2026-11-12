"""What the Questionnaire tab reads (plan.md §7.9; G7, G20, G42, G44, G49, G133, G136). Never writes (G26).

- `deal_forms(deal)`: `GET deals/{id}/questionnaires/` — the chips (armed forms, then started ones), each with its
  progress and signature, and both checklist items as resolved (choice, source, band, the band notice). An empty
  `forms` list hides the tab (G7).
- `form_payload(deal, form_key)`: `GET …/{form}/` — every slot's effective value on screen, its status and source,
  the rows, the slots in the Form's order and the blank required ones, each dependent picker's option key, progress,
  both signatures and the reopens. The writes answer the same shape, so the tab re-reads nothing after a save.
"""

from django.contrib.auth import get_user_model

from deals.selectors import person

from .. import forms, slots, values
from ..engine import walk
from ..engine.conditions import block_visible
from ..engine.options import option_key
from . import context

SOURCE_KEYS = ('origin', 'by', 'at', 'doc', 'page', 'low', 'mark', 'confirmed', 'link')


def _names(ids):
    wanted = {pk for pk in ids if pk}
    if not wanted:
        return {}
    return {user.pk: person(user)['name'] for user in get_user_model().objects.filter(pk__in=wanted)}


def _signature(row, who, names):
    signed_at = getattr(row, f'{who}_signed_at', None) if row else None
    if signed_at is None:
        return None
    by = getattr(row, f'{who}_signed_by_id')
    out = {'name': getattr(row, f'{who}_name'), 'signed_at': signed_at, 'by': by, 'by_name': names.get(by, '')}
    if who == 'officer':
        out.update(authorized=row.officer_authorized, link=row.officer_link)
    return out


def _item_state(resolved, row):
    """One checklist item as the tab and the pickers show it."""
    signed = bool(row and row.officer_signed_at)
    return {**resolved, 'label': forms.label(resolved['form']), 'signed': signed}


def progress_of(form_key, row, facts_and_order):
    view = context.form_view(form_key, row, facts_and_order)
    return walk.progress(view.form, view.view)


def deal_forms(deal, ctx=None):
    ctx = ctx or context.deal_context(deal)
    keys = context.chips(ctx)
    facts_and_order = context.prefill_facts(deal) if keys else None
    out = []
    for key in keys:
        row = ctx.stored.get(key)
        form = forms.FORMS[key]
        out.append(
            {
                'key': key,
                'label': forms.label(key),
                'kind': form['kind'],
                'item': forms.item_of(form),
                'armed': context.armed(ctx, key),
                'started': context.started(row),
                'signed': bool(row and row.officer_signed_at),
                'progress': progress_of(key, row, facts_and_order),
            }
        )
    items = {}
    for item, resolved in ctx.resolved.items():
        row = ctx.stored.get(resolved['form']) or ctx.stored.get(resolved['choice'])
        items[item] = _item_state(resolved, row)
    count = ctx.headcount['count']
    return {
        'forms': out,
        'items': items,
        'headcount': {key: ctx.headcount[key] for key in ('count', 'source', 'estimate')},
        'band': forms.band(count),
    }


def _sources(stored, on_screen):
    out = {}
    for slot in on_screen:
        entry = stored.sources.get(slot)
        if isinstance(entry, dict) and slot in stored.answers:
            out[slot] = {key: entry[key] for key in SOURCE_KEYS if key in entry}
    return out


def _rows(view):
    return {
        block: [
            {'id': row['id'], 'number': index + 1, 'origin': row.get('origin', ''), 'plan': row.get('plan')}
            for index, row in enumerate(view.stored.rows.get(block) or [])
        ]
        for block in (view.form.get('blocks') or {})
    }


def state_of(view):
    """The form's state after a read or a write: values, statuses, rows, order, blanks, option keys, progress."""
    form, stored, live, shown = view.form, view.stored, view.prefill, view.view
    order = walk.order(form, shown)
    on_screen = [entry['slot'] for entry in order]
    scalars, by_block = shown
    option_keys = {}
    for slot in on_screen:
        block, row_id, field = slots.parse(slot)
        if not block:
            continue
        row_values = next((v for rid, v in by_block.get(block) or [] if rid == row_id), {})
        found = option_key(form, block, row_values, field)
        if found:
            option_keys[slot] = found
    shown_values = {}
    for slot in on_screen:
        value = values.effective(stored, live, slot)
        if value not in (None, ''):
            shown_values[slot] = value
    return {
        'values': shown_values,
        'status': values.statuses(form, stored, live, shown),
        'sources': _sources(stored, on_screen),
        'rows': _rows(view),
        'blocks': [key for key in (form.get('blocks') or {}) if block_visible(form, key, scalars)],
        'order': on_screen,
        'blanks': walk.blanks(form, shown),
        'options': option_keys,
        'progress': walk.progress(form, shown),
        'cleared': sorted(stored.cleared),
        'waiting': sum(1 for entry in stored.client.values() if (entry or {}).get('status') == 'pending'),
    }


def form_payload(deal, form_key, ctx=None):
    ctx = ctx or context.deal_context(deal)
    row = ctx.stored.get(form_key)
    view = context.form_view(form_key, row, context.prefill_facts(deal))
    form = view.form
    names = _names(
        [row.officer_signed_by_id, row.agent_signed_by_id, *[r.get('by') for r in row.reopens or []]] if row else []
    )
    item = forms.item_of(form)
    resolved = ctx.resolved[item]
    return {
        'form': form_key,
        'version': form['version'],
        'form_version': row.form_version if row else form['version'],
        'version_mismatch': bool(row and row.form_version != form['version']),
        'started': context.started(row),
        'armed': context.armed(ctx, form_key),
        'locked': bool(row and row.locked),
        'officer': _signature(row, 'officer', names),
        'agent': _signature(row, 'agent', names),
        'reopens': [{**r, 'by_name': names.get(r.get('by'), '')} for r in (row.reopens if row else [])],
        'item': _item_state(resolved, row if resolved['form'] == form_key else None),
        'lost': deal.stage == 'lost',
        **state_of(view),
    }
