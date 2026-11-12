"""A client's intake answers through a portal link: intake's side of the owner contract (plan.md §5.8, §6.5; L.6,
O.3.1; L83–L86, B43; OQ84). Review's portal calls these, after it has checked what the link asks.

- `save_client(deal_id, link_id, entries, blank=…)`: `entries` is {slot: {value, base}}, a slot being a question key or
  one of the blocks (`block:contacts`, `block:coverage`, `block:lines`). Every value is cleaned by intake's one cleaner
  and every base checked before anything is written: a refused value raises a 400 naming the slots (nothing saved), and
  a stale base comes back in `conflicts` with nothing saved, unless the answer is already what the slot holds ("the
  same value twice" is no conflict). Answers wait in `Intake.client` (client_entries' shape); `answers`, `sources`, the
  coverage rows, the contacts and the lines to quote are never touched (OQ84: they wait for a person). An answer equal
  to the stored value drops a pending one. No Activity here: review records the client's save; the owners record
  approvals (L.6).
- `sign_from_link(deal_id, link_id, name, ip, agent)`: the Broker of Record typed signature from the portal (L86): it
  lands like a person's, by nobody, with the link, the IP and the browser kept with it (OQ86: the IP only here).
Lock order: the Deal, then the Intake row (created by the first save that writes, never by a read).
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.services.snapshots import diff

from .. import client_entries as entries_rule
from .. import client_view, form
from ..models import CurrentCoverage, Intake
from . import bor, rows

Saved = namedtuple('Saved', 'changed conflicts bases')  # changed: [slot]; conflicts: [{slot, theirs, base}]
Signed = namedtuple('Signed', 'changed activity')

NOT_A_SLOT = 'This link does not ask that.'
NOT_SENT = 'Send each answer as {value, base}.'
AGENT_LIMIT = 300


def slots_known(slot):
    return slot in form.KEYS or slot in client_view.BLOCK_SLOTS


def _known_ids(deal):
    contacts = {row['id'] for row in client_view.contact_rows(deal.client_id)}
    coverage = set(CurrentCoverage.objects.filter(deal_id=deal.id).values_list('id', flat=True))
    return {client_view.CONTACTS: contacts, client_view.COVERAGE: coverage, client_view.LINES: set()}


def _cleaned(entries, known):
    out, errors = {}, {}
    for slot, sent in entries.items():
        if not slots_known(slot):
            errors[slot] = NOT_A_SLOT
            continue
        if not isinstance(sent, dict) or 'value' not in sent:
            errors[slot] = NOT_SENT
            continue
        raw = sent['value']
        if slot in client_view.BLOCK_SLOTS:
            value, error = client_view.clean_block(slot, raw, known[slot])
        else:
            value, error = client_view.clean_answer(slot, raw)
        if error:
            errors[slot] = error
        else:
            out[slot] = value
    if errors:
        raise ValidationError({'answers': errors})
    return out


@transaction.atomic
def save_client(deal_id, link_id, entries, *, blank=False):
    """Returns Saved([slots written], [conflicts], {slot: new base}). Raises ValidationError (400) before writing."""
    deal = rows.lock_deal(deal_id)
    cleaned = _cleaned(entries, _known_ids(deal))
    intake = Intake.objects.select_for_update().filter(deal_id=deal_id).first()
    stored = client_view.stored(deal, intake)
    client = dict((intake.client if intake else None) or {})
    sources = (intake.sources if intake else None) or {}
    now = clock.now().isoformat()
    conflicts, changed = [], []
    for slot, value in cleaned.items():
        entry = client.get(slot)
        source = sources.get(slot) if slot in form.KEYS else None
        current = stored.get(slot, '' if slot in form.KEYS else [])
        shown = entries_rule.shown(current, entry, link_id, blank=blank)
        held = entries_rule.base(source, entry, link_id, blank=blank)
        if entries[slot].get('base') != held:
            if not entries_rule.same(shown, value):
                conflicts.append({'slot': slot, 'theirs': shown, 'base': held})
            continue
        after, moved = entries_rule.next_entry(current, entry, value, link_id, now)
        if not moved:
            continue
        if after is None:
            client.pop(slot, None)
        else:
            client[slot] = after
        changed.append(slot)
    if conflicts:
        return Saved([], conflicts, {})
    if changed:
        intake = intake or rows.lock_intake(deal_id)
        intake.client = client
        intake.save(update_fields=['client', 'updated_at'])
    bases = {}
    for slot in cleaned:
        source = sources.get(slot) if slot in form.KEYS else None
        bases[slot] = entries_rule.base(source, client.get(slot), link_id, blank=blank)
    return Saved(changed, [], bases)


@transaction.atomic
def sign_from_link(deal_id, link_id, name, ip, agent):
    """The BOR signed on the portal. Signing again under the same name changes nothing. Returns Signed(changed,
    Activity row or None); intake's `bor` row, written for the client (actor_kind client), keeps the signer's name as
    a person's signature does (the employer's officer, not a census member; §3.8)."""
    name = bor.clean_name(name)
    deal = rows.lock_deal(deal_id)
    intake = rows.lock_intake(deal_id)
    if intake.bor_signed_at is not None and intake.bor_name == name:
        return Signed({}, None)
    before = bor.state(intake)
    via = {'link': link_id, 'ip': str(ip or '')[:64], 'agent': str(agent or '')[:AGENT_LIMIT]}
    bor.put(intake, {'name': name, 'signed_at': clock.now(), 'signed_by': None, 'via': via})
    changed = diff(before, bor.state(intake))
    row = activity.record(
        deal,
        None,
        rows.AREA,
        bor.ACTION,
        'The client signed the BOR on their link (typed signature)',
        changes=[activity.change(bor.target(deal.id), changed)],
        actor_kind='client',
    )
    return Signed(changed, row)
