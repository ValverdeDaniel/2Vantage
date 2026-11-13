"""The Ask card's numbers (plan.md §7.13 `POST review/requests/{rid}/form/?dry_run=1`; L42; old 891f1b3
`link_form.dry_run`): the same plan as Update link (`services.form.prepare`), read and never written, in the words a
person can act on.

`preview(user, deal_id, request_id, data)` → Previewed(asks, adds, offs, floor, level, owed, refused, warnings,
numbers): what the request asks once the change goes (`asks`, a phrase each) and the phrases it adds and takes off;
the lowest level that allows it and what set it (`floor`), the level it would have (`level`) and whether a raise is
owed first (`owed`, then `refused` says so); why else it cannot go; what a person should know first (a client
question open on something coming off stays on our side; a link left asking nothing); and the live numbers of what
its first live link would ask (`selectors.drafted.numbers`). Makes no PIN. `asks_after` is what their form in the
middle shows (`POST review/preview/`).
"""

from collections import namedtuple

from rest_framework.exceptions import ValidationError

from deals import activity, clock

from ..models import ClientRequest, ReviewNote
from ..rules import ask_words, form_plan, policy
from ..rules import asks as ask_rules
from ..rules import join as join_rules
from ..rules import tray as tray_rules
from ..selectors import drafted
from ..selectors import notes as note_rows
from . import form, link_settings

Previewed = namedtuple('Previewed', 'asks adds offs floor level owed refused warnings numbers')

NOTHING_LEFT = 'This leaves the link asking nothing. It still opens, with nothing on it: turn it off if you are done.'
QUESTION_STAYS = '{label}: a question of theirs is open. It leaves their page and stays on yours until you answer it.'


def first(detail):
    """The first sentence of a refusal's detail (a dict of lists, a list, or a sentence)."""
    if isinstance(detail, dict):
        if 'detail' in detail:
            return first(detail['detail'])
        for value in detail.values():
            return first(value)
    if isinstance(detail, list) and detail:
        return first(detail[0])
    return str(detail)


def _warnings(deal, body, planned, items):
    out = []
    asked = {note_rows.ref_of(note) for note in ReviewNote.objects.filter(
        deal=deal, kind='question', resolved_at__isnull=True)}  # fmt: skip
    for ref in planned.removed:
        if ref in asked:
            out.append(QUESTION_STAYS.format(label=items[ref].label if ref in items else ref))
    if form_plan.touches(body.change) and ask_rules.is_empty(planned.asks):
        out.append(NOTHING_LEFT)
    return out


def _settings_refused(body, links, now):
    by_id = {link.id: link for link in links}
    for pk, own in body.settings.items():
        try:
            if own.get('expires_on'):
                link_settings.expiry_of(by_id[pk], own['expires_on'], now)
        except ValidationError as refused:
            return first(refused.detail)
    return ''


def _ticked_floor(deal, request, body):
    """The floor of what is ticked, for a dry run refused because the level is too low."""
    drafts = form.drafts_of(deal, request, body.ids, lock=False)
    try:
        planned = form_plan.plan(request.asks, body.change, add=[note_rows.ref_of(note) for note in drafts])
    except join_rules.TooMany:
        return policy.floor(request.asks)
    return policy.floor(planned.asks)


def asks_after(deal, request, data):
    """(asks, why): what an open request would ask with the Ask card's ticks on it, whatever level is owed (their form
    shows what a raise is for); a change that cannot go shows the request as it stands, with why (L30)."""
    try:
        body = form.parse(data)
        drafts = form.drafts_of(deal, request, body.ids, lock=False)
        planned = form_plan.plan(request.asks, body.change, add=[note_rows.ref_of(note) for note in drafts])
    except (ValidationError, join_rules.TooMany) as refused:
        return request.asks, first(getattr(refused, 'detail', form.TOO_MANY))
    return planned.asks, ''


def preview(user, deal_id, request_id, data):  # noqa: ARG001 (a service's signature)
    form.check(deal_id, request_id)
    body = form.parse(data)
    request = ClientRequest.objects.select_related('deal__client').get(pk=request_id)
    deal = request.deal
    links = list(request.links.order_by('id'))
    now = clock.now()
    level = body.security or tray_rules.weakest(links, now)
    base = Previewed(ask_words.words(request.asks), [], [], policy.floor(request.asks), level, False, '', [], {})
    try:
        planned, level, floor, _drafts, items, live = form.prepare(deal, request, links, body, now, lock=False)
    except form.NeedsLevel as owed:
        return base._replace(refused=first(owed.detail), owed=True, floor=_ticked_floor(deal, request, body))
    except (activity.Refused, ValidationError) as refused:
        return base._replace(refused=first(refused.detail))
    was, after = ask_words.words(request.asks), ask_words.words(planned.asks)
    return Previewed(
        asks=after,
        adds=[phrase for phrase in after if phrase not in was],
        offs=[phrase for phrase in was if phrase not in after],
        floor=floor,
        level=level,
        owed=False,
        refused=_settings_refused(body, links, now),
        warnings=_warnings(deal, body, planned, items),
        numbers=drafted.numbers(deal, planned.asks, request=request, link=live[0]),
    )
