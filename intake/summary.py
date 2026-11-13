"""Intake's facts for Agenda and the Overview (plan.md §5.10, O.2; B35): `facts(deal_ids) -> {deal_id: dict}` —
counts, dates and flags only, the same for every viewer. The next step "Complete intake" or "Mark as marketed" reads
`ready_state` and `gaps`; the journey reads `answered` of `needed`. Agenda's intake steps (slice 60; I44, I46) read
`blockers` (each gap with its kind and key: one step per blocker) and `items` (the checklist's rows with their status,
how each is satisfied and, for the questionnaire rows, the form's state).

Intake's own rows (the deals, their Intake rows, coverage rows, contacts and files) are read in a fixed number of
queries however many deals are asked. The four provider slots (headcount, Census OK, the questionnaire forms and the
plans' lines; O.1) answer one deal at a time, inside one batch scope (`deals.batch`; slice 61), so the rows behind
them are read once for every deal: the same queries for 1 deal or 300 (Q.3 #4).
"""

from collections import defaultdict

from deals import batch
from deals.models import Contact
from documents.models import Document

from . import gate, providers, selectors
from .models import CurrentCoverage, Intake


def _grouped(rows, key):
    found = defaultdict(list)
    for row in rows:
        found[key(row)].append(row)
    return found


ITEM_KEYS = ('key', 'label', 'satisfy', 'kind', 'status', 'has_document', 'form_key', 'signed', 'needed')


def facts(deal_ids):
    """{deal_id: {answered, needed, missing, contacts_ok, bor_on_file, census_ok, ready_state, gaps, blockers: [{kind,
    key, label}], checklist: {tier, required, done, missing, all_clear}, items: [{key, label, satisfy, kind, status,
    has_document, form_key, signed, needed}], marketed_at, readiness_pct}} for the deals asked (unknown ids are left
    out)."""
    with batch.scope(deal_ids):
        return _facts(deal_ids)


def _facts(deal_ids):
    deals = batch.deals(deal_ids)
    ids = [deal.id for deal in deals]
    intakes = {row.deal_id: row for row in Intake.objects.filter(deal_id__in=ids)}
    coverage = _grouped(
        CurrentCoverage.objects.filter(deal_id__in=ids).order_by('sort_order', 'id'), lambda r: r.deal_id
    )
    people = _grouped(
        Contact.objects.filter(client_id__in={deal.client_id for deal in deals}).order_by('sort_order', 'id'),
        lambda c: c.client_id,
    )
    files = _grouped(
        Document.objects.filter(deal_id__in=ids, protected=False)  # as `gate.documents_of`: no copy the app filed
        .exclude(review_state='wrong')
        .order_by('id')
        .values_list('deal_id', 'id', 'kind', 'lines', 'label', 'original_name'),
        lambda f: f[0],
    )
    found = {}
    for deal in deals:
        intake, rows = intakes.get(deal.id), coverage.get(deal.id, [])
        contacts = people.get(deal.client_id, [])
        documents = [(doc_id, kind, lines, label or name) for _d, doc_id, kind, lines, label, name in files[deal.id]]
        quote_lines = providers.quote_lines(deal.id)
        state = selectors.form_state(deal, intake, rows, quote_lines, contacts)
        answers = selectors.answers_of(deal, intake)
        read = gate.read(
            deal,
            intake,
            rows=rows,
            quote_lines=quote_lines,
            intent=selectors.card(deal, rows, quote_lines, intake, documents),
            documents=documents,
            answers=answers,
            needed=state['needed'],
            contacts=contacts,
        )
        card, ready = read['checklist'], read['ready']
        found[deal.id] = {
            'answered': state['readiness']['answered'],
            'needed': state['readiness']['needed'],
            'missing': [entry['label'] for entry in ready['gaps'] if entry['kind'] == 'question'],
            'contacts_ok': ready['contacts_ok'],
            'bor_on_file': ready['bor_on_file'],
            'census_ok': ready['census_ok'],
            'ready_state': ready['state'],
            'gaps': [entry['label'] for entry in ready['gaps']],
            'blockers': [{key: entry[key] for key in ('kind', 'key', 'label')} for entry in ready['gaps']],
            'checklist': {key: card[key] for key in ('tier', 'required', 'done', 'missing', 'all_clear')},
            'items': [{key: row.get(key) for key in ITEM_KEYS} for row in card['items']],
            'marketed_at': intake.marketed_at if intake else None,
            'readiness_pct': state['readiness']['pct'],  # the sidebar's Intake meter (A23; slice 61)
        }
    return found
