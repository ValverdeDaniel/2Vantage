"""A client's answers through their link: Save, Submit and the BOR signature (plan.md §5.8, §7.14; L.6 `portal/save`,
L83–L90, L95–L98; OQ84, OQ86). The portal's views call these once the guard has let the link through.

`save(link_id, answers)`: `answers` is {ref: {value, base}}, refs as `rules.requests.carries` names them
(`intake:<key>`, `intake:block:<block>`, `census:<member id>:<column>`). In one transaction:
1. every ref must be one this link asks now (`portal.asked`): anything else refuses the whole save (400), so the page
   can never write past its allowlist;
2. the owners take their part through their own doors, intake then census (`save_client`; the chain's order), each
   cleaning by its own rules and checking every base; a refused value is a 400 naming the refs, a stale base a 409
   listing the conflicts, and either way nothing is saved (all or nothing);
3. the link is locked last (Deal → owners → request → link, the staff services' order) and checked again: turned off
   or closed meanwhile, the save is refused with the 410 and rolled back; then `last_saved_at` and the slide.
An answer equal to what the slot holds writes nothing; a save that writes nothing stamps nothing. Saves coalesce into
one Activity row per link ("Client saved 4 answers", key-only).

`submit(link_id, answers)`: the same save, then `submitted_at` (and `first_submitted_at` the first time, B6) and one
attestation of the request's `form_version` (L88); it never slides the expiry (L62). Its own Activity row.
`sign_bor(link_id, name, ip, agent)`: the BOR typed signature, through intake (L86), with the IP and browser kept on
the signature alone (OQ86).
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from census.services import client as census_client
from deals import clock
from intake.services import client as intake_client

from ..models import ClientLink
from ..portal import guard
from ..portal.asked import asked, refs
from . import common, stamps

Saved = namedtuple('Saved', 'link saved bases activity')
Submitted = namedtuple('Submitted', 'link saved bases activity')

NOT_ASKED = 'This link does not ask that.'
NOT_ANSWERS = 'Send the answers as an object of {value, base} by item.'
CONFLICT = 'Someone at your company changed this while you had the page open.'
BOR_NOT_ASKED = 'This link does not ask for the Broker of Record signature.'


class Conflicts(guard.Answer):
    """409: someone else changed these since the page read them; nothing was saved (L96). `theirs` keeps its shape."""

    status_code = 409
    default_code = 'conflict'

    def __init__(self, conflicts):
        super().__init__({'detail': CONFLICT, 'conflicts': conflicts})


def _split(answers, allowed):
    """({intake slot: sent}, {member id: {column: sent}}) from the refs; 400 for any ref this link does not ask."""
    if not isinstance(answers, dict):
        raise ValidationError({'answers': NOT_ANSWERS})
    bad = {ref: NOT_ASKED for ref in answers if ref not in allowed}
    if bad:
        raise ValidationError({'answers': bad})
    intake, census = {}, {}
    for ref, sent in answers.items():
        area, _, rest = ref.partition(':')
        if area == 'intake':
            intake[rest] = sent
        else:
            member, _, column = rest.partition(':')
            census.setdefault(int(member), {})[column] = sent
    return intake, census


def _errors(error, area):
    detail = error.detail.get('answers', {}) if isinstance(error.detail, dict) else {}
    if area == 'intake':
        return {f'intake:{slot}': str(text) for slot, text in detail.items()}
    return {str(ref): str(text) for ref, text in detail.items()}


def _write(link, request, deal, answers):
    """Owners first, all or nothing. Returns ([refs written], {ref: base})."""
    siblings = list(request.links.values_list('id', flat=True))
    found = asked(link, request, deal, link_ids=siblings)
    intake_part, census_part = _split(answers, refs(found))
    blank = bool(link.blank)
    errors, conflicts, saved, bases = {}, [], [], {}
    if intake_part:
        try:
            done = intake_client.save_client(deal.id, link.id, intake_part, blank=blank)
        except ValidationError as error:
            errors.update(_errors(error, 'intake'))
        else:
            conflicts += [
                {'ref': f'intake:{c["slot"]}', 'theirs': c['theirs'], 'base': c['base']} for c in done.conflicts
            ]
            saved += [f'intake:{slot}' for slot in done.changed]
            bases.update({f'intake:{slot}': base for slot, base in done.bases.items()})
    if census_part:
        try:
            done = census_client.save_client(deal.id, link.id, census_part, blank=blank, makers=siblings)
        except ValidationError as error:
            errors.update(_errors(error, 'census'))
        else:
            conflicts += [
                {'ref': f'census:{c["member"]}:{c["column"]}', 'theirs': c['theirs'], 'base': c['base']}
                for c in done.conflicts
            ]
            saved += [f'census:{member}:{column}' for member, column in done.changed]
            bases.update({f'census:{member}:{column}': base for (member, column), base in done.bases.items()})
    if errors:
        raise ValidationError({'answers': errors})
    if conflicts:
        raise Conflicts(conflicts)
    return saved, bases


def _context(link_id):
    link = ClientLink.objects.select_related('request__deal').get(pk=link_id)
    return link, link.request, link.request.deal


@transaction.atomic
def save(link_id, answers):
    link, request, deal = _context(link_id)
    saved, bases = _write(link, request, deal, answers or {})
    deal, request, link = common.locked_open(link_id)
    if not saved:
        return Saved(link, [], bases, None)
    stamps.saved(link, clock.now())
    row = stamps.client_row(
        deal, link, 'client_saved', 'Client saved', saved, count=len(saved), coalesce=f'review:save:{link.id}',
        noun='answer',
    )  # fmt: skip
    return Saved(link, saved, bases, row)


@transaction.atomic
def submit(link_id, answers):
    link, request, deal = _context(link_id)
    saved, bases = _write(link, request, deal, answers or {})
    deal, request, link = common.locked_open(link_id)
    now = clock.now()
    if saved:
        link.last_saved_at = now
    link.submitted_at = now
    link.first_submitted_at = link.first_submitted_at or now
    link.attested_form_version = request.form_version
    link.save(update_fields=['last_saved_at', 'submitted_at', 'first_submitted_at', 'attested_form_version'])
    row = stamps.client_row(deal, link, 'client_submitted', 'Client submitted their answers', saved)
    return Submitted(link, saved, bases, row)


@transaction.atomic
def sign_bor(link_id, name, ip, agent):
    link, request, deal = _context(link_id)
    found = asked(link, request, deal, link_ids=[link.id])
    if 'bor' not in found.blocks:
        raise ValidationError({'name': [BOR_NOT_ASKED]})
    signed = intake_client.sign_from_link(deal.id, link.id, name, ip, agent)
    deal, request, link = common.locked_open(link_id)
    if signed.changed:
        stamps.saved(link, clock.now())
    return signed
