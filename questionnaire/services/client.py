"""A client's questionnaire answers and rows through a portal link: the questionnaire's side of the owner contract
(plan.md §5.8, §6.8, §7.14; L.6, O.3.1, O.3.4; G85–G88, G93, L91; OQ84, OQ85; slice 58). Review's portal calls these
after it has checked what the link asks; nothing here knows a token.

- `save_client(deal_id, link_id, form_key, entries, picks=…, blank=…)`: `entries` is {slot: {value, base}}. Every
  value goes through the form's one cleaner (`cleaning.clean_batch`, against the form as the link shows it) and every
  base is checked before anything is written: a refused value is a 400 naming each slot and why (G88: every refusal
  said, a broker's field included, G86), and a stale base comes back in `conflicts` with nothing saved (the same value
  twice is no conflict). An answer waits in `Questionnaire.client` with the value it would replace (`prior`) and
  never touches `answers`: only a person's approval moves it (OQ84), and nothing prints it until then (OQ85). An
  answer equal to what we hold (the stored value, else the live prefill) drops a pending one; a newer answer from any
  link replaces the waiting one (G88). A SIC code sets its description beside it (G16), waiting the same way.
- `add_row` / `remove_row(deal_id, link_id, form_key, block[, row_id], picks=…)`: "＋ Add another plan" on the link
  (G87): the row is the form's at once (origin `client`, the link), empty until answers in it are approved; the client
  removes only a row their link added that holds no approved answer, and its waiting answers go with it.
A signed form takes nothing (409). The first write makes the form's row (by nobody, `common.open_row`). No Activity
here: review records the client's save and rows, key-only; the owner records approvals (L.6). Lock order: the Deal,
then intake's row (the first write's band freeze), then the Questionnaire row (`common`).
"""

from collections import namedtuple

from django.db import transaction
from django.http import Http404
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from intake import client_entries as entries_rule

from .. import cleaning, slots
from ..engine.spec import field_spec, get_block
from ..selectors import portal
from . import common

Saved = namedtuple('Saved', 'changed conflicts bases')  # changed: [slot]; conflicts: [{slot, theirs, base}]
Row = namedtuple('Row', 'row_id')

NOT_ASKED = 'This link does not ask that.'
NOT_SENT = 'Send each answer as {value, base}.'
BROKER = 'Your broker fills this in.'
REFUSALS = {
    'unknown': NOT_ASKED,
    'unknown_row': 'That row is no longer on the form.',
    'not_number': 'Type a number here.',
    'not_offered': 'Pick one of the choices offered.',
    'too_long': f'Keep this answer under {cleaning.TEXT_LIMIT:,} characters.',
}
NOT_MINE = 'Only a row you added here can be removed.'
KEPT_ROW = 'Your broker has accepted answers in this row, so it stays.'
ROW_MAX = 'This section allows at most {n} rows.'
ROW_MIN = 'This section needs at least {n} row.'


def _sent(entries):
    if not isinstance(entries, dict):
        raise ValidationError({'answers': {'': NOT_SENT}})
    out, errors = {}, {}
    for slot, sent in entries.items():
        if not isinstance(sent, dict) or 'value' not in sent:
            errors[str(slot)[:120]] = NOT_SENT
        elif isinstance(sent['value'], (list, dict, bool)):
            errors[slot] = REFUSALS['unknown']
        else:
            out[slot] = sent
    if errors:
        raise ValidationError({'answers': errors})
    return out


def _open(deal_id, form_key):
    deal = common.lock_deal(deal_id)
    row, _ctx, facts = common.open_row(None, deal, form_key)
    common.refuse_locked(row)
    return deal, row, facts


@transaction.atomic
def save_client(deal_id, link_id, form_key, entries, *, picks=None, blank=False):
    """Returns Saved. Raises ValidationError (400) before writing; Refused (409) on a signed form."""
    sent = _sent(entries)
    deal, row, facts = _open(deal_id, form_key)
    lv = portal.link_view(deal, form_key, link_id, picks=picks, blank=blank, row=row, facts=facts)
    allowed = portal.writable(lv)
    errors = {slot: (BROKER if _broker(lv, slot) else NOT_ASKED) for slot in sent if slot not in allowed}
    if errors:
        raise ValidationError({'answers': errors})
    cleaned, dropped = cleaning.clean_batch(
        lv.form, lv.view, lv.stored.rows, {slot: one['value'] for slot, one in sent.items()}
    )
    if dropped:
        raise ValidationError({'answers': {item['slot']: REFUSALS[item['reason']] for item in dropped}})
    client = dict(row.client or {})
    now = clock.now().isoformat()
    conflicts, plan = [], []
    for slot, value in cleaned.items():
        held = portal.base_of(lv, slot)
        if slot in sent and sent[slot].get('base') != held:
            theirs = portal.shown_value(lv, slot)
            if not entries_rule.same(theirs, value):
                conflicts.append({'slot': slot, 'theirs': theirs, 'base': held})
            continue
        plan.append((slot, value))
    if conflicts:
        return Saved([], conflicts, {})
    changed = []
    for slot, value in plan:
        ours = portal.held_value(lv, slot)
        prior = row.answers.get(slot, '')
        after, moved = entries_rule.next_entry(ours, client.get(slot), value, link_id, now, prior=prior)
        if not moved:
            continue
        if after is None:
            client.pop(slot, None)
        else:
            client[slot] = after
        changed.append(slot)
    if changed:
        row.client = client
        row.save(update_fields=['client', 'updated_at'])
        lv = lv._replace(stored=lv.stored._replace(client=client))
    return Saved(changed, [], {slot: portal.base_of(lv, slot) for slot in cleaned})


def _broker(lv, slot):
    found = slots.parse(slot)
    field = field_spec(lv.form, found[0], found[2]) if found else None
    return bool(field and field.get('broker'))


def _block(lv, block_key):
    block = get_block(lv.form, block_key)
    if block is None:
        raise Http404('Unknown block.')
    return block


@transaction.atomic
def add_row(deal_id, link_id, form_key, block_key, *, picks=None):
    """Row(the new row's id). 400 past the block's maximum; 404 a block the link does not ask."""
    deal, row, facts = _open(deal_id, form_key)
    lv = portal.link_view(deal, form_key, link_id, picks=picks, row=row, facts=facts)
    block = _block(lv, block_key)
    current = list((row.rows or {}).get(block_key) or [])
    if len(current) >= block['max_rows']:
        raise ValidationError({'block': [ROW_MAX.format(n=block['max_rows'])]})
    row.last_row_id += 1
    entry = {'id': row.last_row_id, 'origin': 'client', 'link': link_id, 'at': clock.now().isoformat()}
    row.rows = {**(row.rows or {}), block_key: [*current, entry]}
    row.save(update_fields=['rows', 'last_row_id', 'updated_at'])
    return Row(entry['id'])


@transaction.atomic
def remove_row(deal_id, link_id, form_key, block_key, row_id, *, picks=None):
    """Row(the removed row's id). 409 for a row another person added or one holding an approved answer."""
    deal, row, facts = _open(deal_id, form_key)
    lv = portal.link_view(deal, form_key, link_id, picks=picks, row=row, facts=facts)
    block = _block(lv, block_key)
    current = list((row.rows or {}).get(block_key) or [])
    entry = next((r for r in current if r['id'] == row_id), None)
    if entry is None:
        raise Http404('That row is not on this form.')
    if entry.get('origin') != 'client' or entry.get('link') != link_id:
        raise activity.Refused(NOT_MINE)
    if not portal.mine(lv, block_key, entry):
        raise activity.Refused(KEPT_ROW)
    if len(current) <= block['min_rows']:
        raise ValidationError({'block': [ROW_MIN.format(n=block['min_rows'])]})
    prefix = f'{block_key}.{row_id}.'
    row.client = {key: value for key, value in (row.client or {}).items() if not key.startswith(prefix)}
    row.cleared = [slot for slot in row.cleared if not slot.startswith(prefix)]
    row.rows = {**row.rows, block_key: [r for r in current if r['id'] != row_id]}
    row.save(update_fields=['client', 'cleared', 'rows', 'updated_at'])
    return Row(row_id)
