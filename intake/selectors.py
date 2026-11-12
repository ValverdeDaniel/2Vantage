"""Intake as the API sends it (plan.md §7.6; B.6). Reads only: nothing here writes, and a deal with no Intake row
reads as empty (M.5 B34). One read per table, whatever the deal holds: the deal, its Intake row, its coverage rows, its
files' kinds and lines, and quotes' `quote_lines` provider.
"""

from deals import comp, lines
from deals.models import Deal
from documents.models import Document

from . import coverage, providers, values
from .models import CurrentCoverage, Intake

_UNSET = object()
PLAIN = ('id', 'line', 'carrier', 'funding', 'in_force', 'notes', 'on_proposal', 'commission', 'commission_source')
DATES = ('effective_date', 'renewal_date', 'rate_guarantee_through')


def _coverage(deal_id):
    return list(CurrentCoverage.objects.filter(deal_id=deal_id).order_by('sort_order', 'id'))


def intent_rows_for(deal_id):
    """The intent matrix as it stands (coverage.intent_rows over the deal's lines and rows)."""
    requested = Deal.objects.values_list('requested_lines', flat=True).get(pk=deal_id)
    return coverage.intent_rows(lines.LINE_KEYS, requested, _coverage(deal_id))


def coverage_row(row, current=None):
    """One coverage row (§7.6). `from_plans` is the line's current plans' carrier and funding once the Advisor has
    them (§6.5): the editors show those read-only."""
    payload = {key: getattr(row, key) for key in PLAIN}
    payload.update({key: getattr(row, key) for key in DATES})
    payload['label'] = lines.label(row.line)
    payload['commission'] = row.commission or None
    payload['commission_label'] = comp.comp_label(row.commission)
    payload['from_plans'] = current
    return payload


def one_coverage_row(row):
    """A coverage row with its line's `from_plans`, for a write's answer."""
    return coverage_row(row, (providers.quote_lines(row.deal_id).get(row.line) or {}).get('current'))


def _documents(deal_id):
    return list(Document.objects.filter(deal_id=deal_id).values_list('id', 'kind', 'lines'))


def card(deal, coverage_rows=None, quote_lines=None, intake=_UNSET):
    """The Coverage & marketing intent card (B16–B21, B24): its rows, the confirmation, the tally and the gaps."""
    rows_in = _coverage(deal.id) if coverage_rows is None else coverage_rows
    quote_lines = providers.quote_lines(deal.id) if quote_lines is None else quote_lines
    if intake is _UNSET:
        intake = Intake.objects.filter(deal_id=deal.id).first()
    confirmed = (intake.intent_confirmed if intake else None) or {}
    rows = coverage.intent_rows(lines.LINE_KEYS, deal.requested_lines, rows_in)
    by_line = coverage.documents_by_line(_documents(deal.id), [row['line'] for row in rows])
    expected = on_file = 0
    for row in rows:
        present = by_line.get(row['line'], {})
        row['label'] = lines.label(row['line'])
        row['documents'] = {kind: list(present.get(kind, ())) for kind in coverage.DOC_KINDS}
        row['needs_documents'] = coverage.needs_documents(row['in_force'], row['this_year'])
        row['from_plans'] = (quote_lines.get(row['line']) or {}).get('current')
        if row['needs_documents']:
            expected += len(coverage.DOC_KINDS)
            on_file += sum(1 for kind in coverage.DOC_KINDS if present.get(kind))
    state = coverage.confirmation(confirmed, rows)
    recorded = bool(deal.requested_lines) or bool(confirmed)
    return {
        'rows': rows,
        'state': state,
        'confirmed': state == 'done',
        'stale': state == 'stale',
        'confirmed_at': confirmed.get('at'),
        'confirmed_by': confirmed.get('by_name', ''),
        'counts': coverage.counts(rows),
        'documents_expected': expected,
        'documents_on_file': on_file,
        'documents_missing': expected - on_file,
        'line_states': coverage.line_states(rows, quote_lines),
        'lines_off': coverage.lines_off(rows, quote_lines, recorded),
    }


def line_facts(deal, quote_lines):
    """(line_states, lines_off) for an app on the right that holds its own plan facts (`quote_lines`' shape; only
    `sold` is read): the Advisor's line tabs (F13) and the proposal's lines (J2, J52) read the card's one rule."""
    rows = coverage.intent_rows(lines.LINE_KEYS, deal.requested_lines, _coverage(deal.id))
    confirmed = Intake.objects.filter(deal_id=deal.id).values_list('intent_confirmed', flat=True).first() or {}
    recorded = bool(deal.requested_lines) or bool(confirmed)
    return coverage.line_states(rows, quote_lines), coverage.lines_off(rows, quote_lines, recorded)


def intake_payload(deal):
    """GET deals/{id}/intake/ (§7.6): the answers and their sources, the hidden questions, the coverage rows and the
    intent card. Slices 39 and 40 add the issues, the checklist, the BOR and the ready state."""
    intake = Intake.objects.filter(deal_id=deal.id).first()
    answers = intake.answers if intake else {}
    rows = _coverage(deal.id)
    quote_lines = providers.quote_lines(deal.id)
    return {
        'answers': answers,
        'sources': intake.sources if intake else {},
        'hidden': values.hidden(answers),
        'coverage': [coverage_row(row, (quote_lines.get(row.line) or {}).get('current')) for row in rows],
        'intent': card(deal, rows, quote_lines, intake),
    }
