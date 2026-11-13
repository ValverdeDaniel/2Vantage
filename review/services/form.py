"""The Ask card's Update link: what an open request asks, its level and each person's settings, in one locked write
(plan.md §5.8, §7.13 `POST review/requests/{rid}/form/[?dry_run=1]`; L42, L59, L36, L39, L64; old 891f1b3
`review/link_form.py`).

`update(user, deal_id, request_id, data)` → Updated(request, changed, pins, sent, closed, activity). The body:
- `ids`: the tray's drafts that go on (a tick on the Ask card is a draft named for the request, L42 "ticks are
  drafts"); left out, every draft named for this request;
- `off` {refs, columns, parts} and `on` {intake, census, columns, census_file, documents_missing, blocks}: what comes
  off and what is switched on (`rules.form_plan`); `message`: the note at the top of their page;
- `security`: the level everyone on the request gets (link or pin). A link already out is never raised by itself:
  what is ticked needing more than the links have answers 409 `needs_level` until a person raises it (L42, L64); a
  raise makes a PIN for each live link, shown this once; a level may fall once what needed it comes off;
- `settings` {link id: {blank?, expires_on?, nudge_on?}}: each person's own, last (`services.link_settings`).
Order (L42): removals, the level, what is added, then the settings; one transaction under the Deal, the request and
its links by id. Asks that changed bump `form_version` (their open page re-reads), send asks the request no longer
carries are closed, and if anything was added every live link gets its life again (old "lives again when sent"). A
body that says nothing about the form leaves what a link asks alone (D-188 #5).

The dry run (`form_preview.preview`) reads the same plan (`prepare`) and writes nothing. One Activity row (area
review): the asks before and after (refs and keys, never a value), the level and each setting; not revertible, since
the change reached the client (as a tray send).
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from census import client_view as census_view
from census import facts as census_facts
from deals import activity, clock

from .. import words
from ..models import ASK_KINDS, ClientRequest, ReviewNote
from ..rules import ask_words, form_plan, policy
from ..rules import join as join_rules
from ..rules import tray as tray_rules
from ..selectors import items as item_rows
from ..selectors import notes as note_rows
from . import common, link_settings, pins
from .deliver import TOO_MANY, carried

Updated = namedtuple('Updated', 'request changed pins sent closed activity')
Body = namedtuple('Body', 'change ids security message settings')

NEEDS_LEVEL = '{what} needs at least {level}: raise this link, or leave it off.'
NOT_ALONE = '{labels}: asked as part of {part} on this link. Switch it to picked questions, or take {part} off.'
NO_LIVE = 'No link on this request can open again: make a new link instead.'
NOT_ON_REQUEST = 'That person is not on this request.'
PARTS = {'intake': 'the intake', 'census': 'the census', 'doc': 'the missing documents'}


def _ids(raw):
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(isinstance(pk, int) and not isinstance(pk, bool) for pk in raw):
        raise ValidationError({'ids': ['Send the ids as a list of numbers.']})
    return raw


def _settings(raw, errors):
    if raw in (None, {}):
        return {}
    if not isinstance(raw, dict):
        errors['settings'] = ['Send each link’s settings as an object.']
        return {}
    out = {}
    for key, wanted in raw.items():
        if not str(key).isdigit() or not isinstance(wanted, dict):
            errors['settings'] = ['Send each link’s settings as an object, by link id.']
            continue
        own = {}
        if 'blank' in wanted:
            if wanted['blank'] not in (True, False):
                errors['settings'] = ['blank must be true or false.']
            own['blank'] = wanted['blank'] is True
        if wanted.get('expires_on'):
            own['expires_on'] = link_settings._day(wanted['expires_on'], 'expires_on')
        if 'nudge_on' in wanted:
            own['nudge_on'] = link_settings._day(wanted['nudge_on'], 'nudge_on')
        out[int(key)] = own
    return out


def parse(data):
    if not isinstance(data, dict):
        raise ValidationError({'non_field_errors': ['Send the change as an object.']})
    change, errors = form_plan.parse(data)
    security = str(data.get('security') or '')
    if security and security not in policy.LEVELS:
        errors['security'] = [words.BAD_LEVEL]
    message = data.get('message')
    if message is not None:
        message = str(message).strip()
        if len(message) > policy.MESSAGE_LIMIT:
            errors['message'] = [words.MESSAGE_LONG.format(limit=policy.MESSAGE_LIMIT)]
    settings = _settings(data.get('settings'), errors)
    ids = _ids(data.get('ids'))
    if errors:
        raise ValidationError(errors)
    return Body(change, ids, security, message, settings)


def drafts_of(deal, request, ids, *, lock):
    rows = ReviewNote.objects.filter(deal=deal, kind__in=ASK_KINDS, sent_at__isnull=True, resolved_at__isnull=True)
    rows = rows.filter(pk__in=ids) if ids is not None else rows.filter(request=request)
    if lock:
        rows = rows.select_for_update()
    return list(rows.order_by('id'))


def _refusal(refs, items):
    by_part = {}
    for ref in refs:
        part = ref.split(':', 1)[0]
        label = items[ref].label if ref in items else ref
        by_part.setdefault(PARTS.get(part, 'the form'), []).append(label)
    part, labels = next(iter(by_part.items()))
    return NOT_ALONE.format(labels=', '.join(labels[:5]), part=part)


class NeedsLevel(activity.Refused):
    """What is ticked needs more than the links have, and only a person raises a link already out (409 needs_level)."""

    def __init__(self, floor):
        what = ' and '.join(floor['because']) or 'This'
        sentence = NEEDS_LEVEL.format(what=what, level=words.LEVEL_NEEDS.get(floor['level'], floor['level']))
        super().__init__(sentence)
        self.detail = {'detail': sentence, 'needs_level': floor['level']}
        self.floor = floor


def prepare(deal, request, links, body, now, *, lock):
    """(planned, level, floor, drafts, items, live). Raises Refused or ValidationError."""
    common.refuse_unless_asking(deal, request)
    live = tray_rules.live_links(links, now)
    if not live:
        raise activity.Refused(NO_LIVE)
    on_request = {link.id for link in links}
    if bad := [pk for pk in body.settings if pk not in on_request]:
        raise ValidationError({'settings': [NOT_ON_REQUEST + f' ({bad[0]})']})
    drafts = drafts_of(deal, request, body.ids, lock=lock)
    refs = [note_rows.ref_of(note) for note in drafts]
    items = item_rows.resolve(deal, [*refs, *body.change.off_refs])
    adds = [ref for ref in refs if ref in items and not items[ref].gone]
    held = carried(deal, request, live[0], links)
    columns = census_view.columns(deal, census_facts.needed(deal))
    try:
        planned = form_plan.plan(request.asks, body.change, add=adds, carried=held, columns=columns['employee'])
    except join_rules.TooMany:
        raise activity.Refused(TOO_MANY) from None
    if planned.refused:
        raise activity.Refused(_refusal(planned.refused, items))
    current = tray_rules.weakest(links, now)
    level = body.security or current
    floor = policy.floor(planned.asks)
    if policy.RANK[level] < policy.RANK[floor['level']]:
        raise NeedsLevel(floor)
    return planned, level, floor, drafts, items, live


def _level(links, level, now):
    """{link id: (before, after)} and {link id: pin}: everyone on the request gets the level (L64), a link turned off
    too while it could be turned back on (it would open at the old level otherwise)."""
    diffs, made = {}, {}
    for link in links:
        if link.security == level or not policy.can_renew(link, now):
            continue
        diffs[link.id] = {'security': [link.security, level]}
        link.security = level
        if level == policy.PIN:
            made[link.id] = pins.issue(link)
        else:
            link.pin_hash, link.pin_tries = '', 0
        link.save(update_fields=['security', 'pin_hash', 'pin_tries', 'pin_version'])
    return diffs, made


def _close_off(user, deal, request, links, now):
    """Close the sent asks on this request that it no longer carries (they leave the client's page)."""
    still = carried(deal, request, links[0], links) if links else set()
    sent = ReviewNote.objects.filter(request=request, kind__in=ASK_KINDS, sent_at__isnull=False,
                                     resolved_at__isnull=True).select_for_update()  # fmt: skip
    gone = [note.id for note in sent if note_rows.ref_of(note) not in still]
    if gone:
        ReviewNote.objects.filter(pk__in=gone).update(resolved_at=now, resolved_by_id=common.user_id(user))
    return len(gone)


def _summary(before, after, level_changed, level):
    was, now = ask_words.words(before), ask_words.words(after)
    parts = [f'+ {phrase}' for phrase in now if phrase not in was]
    parts += [f'− {phrase}' for phrase in was if phrase not in now]
    if level_changed:
        parts.append(next(row['label'] for row in words.LEVELS if row['key'] == level))
    return 'Updated a client link' + (f': {" · ".join(parts[:6])}' if parts else '')


def _settings_write(user, deal, links, settings, now):
    out = {}
    by_id = {link.id: link for link in links}
    for pk, own in sorted(settings.items()):
        link = by_id[pk]
        if link.revoked_at is not None:
            continue  # turned off since: nothing to set, nothing to hold up (old D-208)
        diff = {}
        if 'blank' in own:
            diff.update(link_settings.put_blank(link, own['blank']))
        if own.get('expires_on'):
            diff.update(link_settings.put_expiry(deal, user, link, own['expires_on'], now))
        if 'nudge_on' in own:
            diff.update(link_settings.put_nudge(user, link, own['nudge_on'], now))
        if diff:
            out[pk] = diff
    return out


def _revive(live, now):
    for link in live:
        moved = policy.renewed(link.expires_at, link.ceiling_at, now)
        if moved != link.expires_at:
            link.expires_at = moved
            link.save(update_fields=['expires_at'])


def grows(change):
    """True when the change switches something on (a link then gets its life again, as when an ask joins it)."""
    return bool(change.on_intake or change.on_census or change.on_columns or change.on_file or change.on_missing
                or change.on_blocks)  # fmt: skip


def check(deal_id, request_id):
    if not ClientRequest.objects.filter(pk=request_id, deal_id=deal_id).exists():
        raise ClientRequest.DoesNotExist


@transaction.atomic
def update(user, deal_id, request_id, data):
    """Updated(request, changed, {link id: pin}, sent, closed, Activity row or None)."""
    check(deal_id, request_id)
    body = parse(data)
    deal, request = common.locked_request(request_id)
    links = list(request.links.select_for_update().order_by('id'))
    now = clock.now()
    planned, level, _floor, drafts, items, live = prepare(deal, request, links, body, now, lock=True)
    before = request.asks
    changed = {}
    if planned.changed and (form_plan.touches(body.change) or planned.added):
        changed['asks'] = [before, planned.asks]
        changed['form_version'] = [request.form_version, request.form_version + 1]
        request.asks, request.form_version = planned.asks, request.form_version + 1
    if body.message is not None and body.message != request.message:
        changed['message'] = [request.message, body.message]
        request.message = body.message
    if changed:
        request.save(update_fields=['asks', 'form_version', 'message'])
    level_diffs, made = _level(links, level, now)
    sent = [note for note in drafts if note_rows.ref_of(note) in items and not items[note_rows.ref_of(note)].gone]
    for note in sent:
        note.request_id, note.sent_at = request.id, now
    ReviewNote.objects.bulk_update(sent, ['request', 'sent_at'])
    ReviewNote.objects.filter(pk__in=[note.id for note in drafts if note not in sent]).delete()
    closed = _close_off(user, deal, request, live, now) if 'asks' in changed else 0
    if 'asks' in changed and (planned.added or grows(body.change)):
        _revive(live, now)
    setting_diffs = _settings_write(user, deal, links, body.settings, now)
    entries = [activity.change(common.request_target(request), changed)] if changed else []
    for pk in sorted(set(level_diffs) | set(setting_diffs)):
        entries.append(activity.change(f'link:{pk}', {**level_diffs.get(pk, {}), **setting_diffs.get(pk, {})}))
    if sent:
        entries.append(activity.change(common.request_target(request), sorted({note_rows.ref_of(n) for n in sent})))
    row = None
    if entries:
        summary = _summary(before, request.asks, bool(level_diffs), level)
        row = activity.record(deal, user, common.AREA, 'updated', summary, changes=entries, revertible=False)
    every = {**changed, **{f'link:{pk}': diff for pk, diff in setting_diffs.items()}}
    every.update({f'link:{pk}': {**every.get(f'link:{pk}', {}), **diff} for pk, diff in level_diffs.items()})
    return Updated(request, every, made, len(sent), closed, row)
