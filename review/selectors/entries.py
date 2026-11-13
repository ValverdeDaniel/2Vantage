"""The client answers waiting on the owners' rows (plan.md §5.8; L.6 "`client_entries(deal)`: one query"; slice 55).

`waiting(deal_ids)` → {deal_id: [Entry]} in two queries however many deals and people: the Intake rows' `client`
entries, then the people whose `client` holds anything (live people's pending cells, and the people a client added who
wait whole). An Entry carries its surface, its ref (`requests.carries`' and the decisions'), the value the client
gave (None for a whole person), its link and when it was given. Slice 58 adds the questionnaires' (a third query):
each form's waiting answers, ref `q:<form>:<slot>`, slot (form, slot) — a signed form's too, which wait for an
approval that files the signed copy.

Reading `Member.client` reads member data: callers count it, or (the queue) show it to staff; it never reaches a log,
an error or Activity (§3.8).
"""

from collections import defaultdict, namedtuple

from census.models import PERSON, Member
from deals import batch
from intake import client_entries as entries_rule
from intake.models import Intake
from questionnaire.models import Questionnaire
from questionnaire.selectors import context as questionnaire_context

from ..models import ClientLink

Entry = namedtuple('Entry', 'deal_id surface ref slot member_id column value link_id at person')


def _entry(deal_id, surface, ref, slot, entry, *, person=False):
    member_id, column = slot if surface == 'census' else (None, None)
    value = None if person else entry.get('value')
    link = entry.get('link')
    return Entry(deal_id, surface, ref, slot, member_id, column, value, link, entry.get('at') or '', person)


def _intake(ids, out):
    for deal_id, client in Intake.objects.filter(deal_id__in=ids).exclude(client={}).values_list('deal_id', 'client'):
        for slot, entry in (client or {}).items():
            if entries_rule.pending(entry):
                out[deal_id].append(_entry(deal_id, 'intake', f'intake:{slot}', slot, entry))


def _census(ids, out):
    found = (
        Member.all_objects.filter(deal_id__in=ids, removed_at__isnull=True)
        .exclude(client={})
        .order_by('position', 'id')
        .values_list('id', 'deal_id', 'client', 'added_by_link')
    )
    for member_id, deal_id, client, maker in found:
        client = client or {}
        whole = client.get(PERSON)
        if maker and entries_rule.pending(whole):
            ref = f'census:{member_id}:{PERSON}'
            out[deal_id].append(_entry(deal_id, 'census', ref, (member_id, PERSON), whole, person=True))
            continue
        if maker and not entries_rule.approved(whole):
            continue  # a person the client added and someone turned away
        for column, entry in client.items():
            if column != PERSON and entries_rule.pending(entry):
                ref = f'census:{member_id}:{column}'
                out[deal_id].append(_entry(deal_id, 'census', ref, (member_id, column), entry))


def _questionnaire(ids, out):
    if ids and all(batch.holds(deal_id) for deal_id in ids):
        # Inside a read's batch scope the forms' rows are read once for every app (Agenda's journey, Q.7).
        rows = sorted(
            (row for deal_id in ids for row in questionnaire_context.stored_rows(deal_id)), key=lambda r: r.id
        )
        found = [(row.deal_id, row.form, row.client) for row in rows if row.client]
    else:
        found = (
            Questionnaire.objects.filter(deal_id__in=ids)
            .exclude(client={})
            .order_by('id')
            .values_list('deal_id', 'form', 'client')
        )
    for deal_id, form_key, client in found:
        for slot, entry in (client or {}).items():
            if entries_rule.pending(entry):
                ref = f'q:{form_key}:{slot}'
                out[deal_id].append(_entry(deal_id, 'questionnaire', ref, (form_key, slot), entry))


def waiting(deal_ids, surfaces=('intake', 'census', 'questionnaire')):
    ids = list(deal_ids)
    out = defaultdict(list)
    if 'intake' in surfaces:
        _intake(ids, out)
    if 'census' in surfaces:
        _census(ids, out)
    if 'questionnaire' in surfaces:
        _questionnaire(ids, out)
    return out


def links_of(entries, known=None):
    """{link id: ClientLink} for the entries' links: `known` (links already loaded), else one query."""
    ids = {entry.link_id for entry in entries if isinstance(entry.link_id, int)}
    if known is not None:
        return {link_id: known[link_id] for link_id in ids if link_id in known}
    return {link.id: link for link in ClientLink.objects.filter(pk__in=ids).select_related('contact')} if ids else {}
