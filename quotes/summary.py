"""Quotes' facts for Agenda and the Overview (plan.md §5.10, O.2; I53–I55, I60, F85–F92): `facts(deal_ids) -> {deal_id:
dict}`, counts, dates and ids only, the same for every viewer. Agenda (slice 60) is the first reader.

Per deal:
- `plans` (live plans), `quotes` (live renewals and alternates: "quotes are in"), `last_quote_at` (the newest quote
  plan's creation, ISO);
- `quote_documents`: [{id, at}] the deal's live files of the quote reader's kinds (`reader.READS`), less a file marked
  the wrong one; `unread`: their ids that no finished read read and no live plan cites (I53);
- `flagged`: plan values to look at — required and blank, or with an open warning (the stored `flags`; I55);
- `sold_lines`: the lines with a sold plan;
- `unpriced`, `unpriced_lines`: plans that no enrollment prices — no census, no typed counts reaching them (the
  precedence of `math.enrollment_for`; F88's `per_plan_counts_needed` among them), on deals with quotes. This is what
  turns Agenda's census step into "Add the census, or type enrollment in the Advisor" (I50, OQ90);
- `required_total`, `required_filled`, `to_review`: over the proposed plans (every plan but the current ones), the
  fields they must hold and how many do, and the values with an open warning: the shell's Proposal meter and badge
  (A21, A23; slice 61; old `proposal_metrics`).

The plans, the files and the reads are one query each whatever the deal count; the unpriced check reads
`selectors.state.deal_state` for each deal with quotes, inside one batch scope (`deals.batch`; slice 61), so its rows
are read once for every deal: the same queries for 1 deal or 300 (Q.3 #4).
"""

from ai import kinds as ai_kinds
from ai.models import Job
from deals import batch
from documents.models import Document

from . import facts as plan_facts
from .models import Plan
from .reader import READS
from .selectors.state import deal_state, scope_plans

QUOTE_ROLES = ('renewal', 'alternate')


def _iso(moment):
    return moment.isoformat() if moment else None


def _required(row):
    """(required, blank) of one plan's values (`facts.required_counts`: `statuses`' missing, without warnings)."""
    return plan_facts.required_counts(row['line'], row['values'] or {})


def _unpriced(deal):
    """(count, [lines]) of the deal's plans no enrollment prices."""
    count, found = 0, []
    for line, state in deal_state(deal).items():
        missing = [pid for pid, result in state.results.items() if result['enrollment_used'] is None]
        if missing:
            count += len(missing)
            found.append(line)
    return count, found


def facts(deal_ids):
    with batch.scope(deal_ids):
        return _facts(list(deal_ids))


def _proposed(found, row, required, blank):
    """The Proposal meter's counts for one proposed plan (old `proposal_metrics`: required filled of required)."""
    if row['role'] == 'current':
        return
    found['required_total'] += required
    found['required_missing'] += blank
    found['to_review'] += row['flags'] or 0


ROW = ('deal_id', 'line', 'role', 'values', 'flags', 'sold', 'created_at', 'source_document_id')


def _rows(ids):
    """The plans' rows: the batch scope's plans when it holds the deals (the steps price those same rows), else one
    query."""
    if ids and batch.holds(ids[0]):
        return [{key: getattr(plan, key) for key in ROW} for deal_id in ids for plan in scope_plans(deal_id)]
    return Plan.objects.filter(deal_id__in=ids).values(*ROW)


def _facts(ids):
    out = {
        deal_id: {
            'plans': 0,
            'quotes': 0,
            'last_quote_at': None,
            'quote_documents': [],
            'unread': [],
            'flagged': 0,
            'sold_lines': [],
            'unpriced': 0,
            'unpriced_lines': [],
            'required_total': 0,
            'required_filled': 0,
            'required_missing': 0,
            'to_review': 0,
        }
        for deal_id in (deal.id for deal in batch.deals(ids))
    }
    cited = {}
    for row in _rows(list(out)):
        found = out[row['deal_id']]
        found['plans'] += 1
        required, blank = _required(row)
        found['flagged'] += (row['flags'] or 0) + blank
        _proposed(found, row, required, blank)
        if row['role'] in QUOTE_ROLES:
            found['quotes'] += 1
            at = _iso(row['created_at'])
            found['last_quote_at'] = max(filter(None, [found['last_quote_at'], at]), default=None)
        if row['sold'] and row['line'] not in found['sold_lines']:
            found['sold_lines'].append(row['line'])
        if row['source_document_id']:
            cited.setdefault(row['deal_id'], set()).add(row['source_document_id'])
    read = {}
    for deal_id, documents in Job.objects.filter(
        deal_id__in=list(out), kind=ai_kinds.READ, status=ai_kinds.DONE
    ).values_list('deal_id', 'documents'):
        read.setdefault(deal_id, set()).update(documents or [])
    files = (
        Document.objects.filter(deal_id__in=list(out), kind__in=READS, protected=False)
        .exclude(review_state='wrong')
        .order_by('id')
        .values_list('deal_id', 'id', 'uploaded_at')
    )
    for deal_id, doc_id, created in files:
        found = out[deal_id]
        found['quote_documents'].append({'id': doc_id, 'at': _iso(created)})
        if doc_id not in read.get(deal_id, set()) and doc_id not in cited.get(deal_id, set()):
            found['unread'].append(doc_id)
    with_quotes = [deal_id for deal_id, found in out.items() if found['quotes']]
    for deal in batch.deals(with_quotes):
        out[deal.id]['unpriced'], out[deal.id]['unpriced_lines'] = _unpriced(deal)
    for found in out.values():
        found['sold_lines'].sort()
        found['required_filled'] = found['required_total'] - found['required_missing']
    return out
