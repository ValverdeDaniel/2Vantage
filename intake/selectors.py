"""Intake as the API sends it (plan.md §7.6; B.6). Reads only: nothing here writes, and a deal with no Intake row
reads as empty (M.5 B34). One read per table, whatever the deal holds: the deal, its Intake row, its coverage rows, its
files' kinds and lines, and quotes' `quote_lines` provider.
"""

from deals import clock, comp, lines
from deals.models import Deal
from documents.models import Document

from . import checklist, coverage, form, providers, status, validation, values
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


def answers_of(deal, intake):
    """The deal's answers as the form shows them: the row's, plus `target_effective_date`, which is a door onto the
    deal's one effective date and lives there (B1, N.1), never in `answers`."""
    answers = dict(intake.answers) if intake else {}
    answers.pop(form.EFFECTIVE_DATE, None)
    if deal.effective_date:
        answers[form.EFFECTIVE_DATE] = deal.effective_date.isoformat()
    return answers


def _medical_funding(rows, quote_lines):
    """The medical line's funding as the deal records it: its current plans' once they exist (§6.5), else its row's."""
    current = (quote_lines.get('medical') or {}).get('current')
    if current:
        return current.get('funding') or ''
    first = coverage.first_rows(rows).get('medical')
    return first.funding if first else ''


def form_state(deal, intake, rows, quote_lines):
    """What the form shows beside the answers (§5.2; B2, B6, B8, B9): the hidden and needed questions, each answer's
    status, the inline checks, the needed questions answered, and the two notes. The answers PATCH answers it too."""
    answers = answers_of(deal, intake)
    sources = intake.sources if intake else {}
    rules = intake.rules if intake else {}
    hidden = values.hidden(answers)
    needed = values.needed_keys(answers, rules)
    pending = status.pending_keys(intake.client if intake else {})
    dated = [{'id': row.id, 'renewal_date': row.renewal_date} for row in rows]
    # Contacts (and their email check) join with slice 40.
    issues = validation.validate_intake(
        answers, coverage=dated, medical_funding=_medical_funding(rows, quote_lines), today=clock.today()
    )
    return {
        'hidden': hidden,
        'needed': needed,
        'status': status.statuses(answers, sources, needed, hidden, pending),
        'issues': issues,
        'readiness': values.readiness(answers, needed),
        'review': status.review_counts(answers, sources, hidden),
        'notes': status.notes(answers, deal.requested_lines),
    }


def intake_payload(deal):
    """GET deals/{id}/intake/ (§7.6): the answers and their sources, the form's state (hidden and needed questions,
    statuses, issues, readiness, notes), the coverage rows and the intent card. Slice 40 adds the contacts, the
    checklist, the BOR and the ready state."""
    intake = Intake.objects.filter(deal_id=deal.id).first()
    rows = _coverage(deal.id)
    quote_lines = providers.quote_lines(deal.id)
    return {
        'answers': answers_of(deal, intake),
        'sources': intake.sources if intake else {},
        **form_state(deal, intake, rows, quote_lines),
        'coverage': [coverage_row(row, (quote_lines.get(row.line) or {}).get('current')) for row in rows],
        'intent': card(deal, rows, quote_lines, intake),
    }


def checklist_item(deal_id, key):
    """One checklist item as a screen shows it (`checklist.item_state`): the door the Census tab reads the COBRA tick
    through (C25, O.6 #2). A deal with no Intake row reads unchecked."""
    from django.contrib.auth import get_user_model

    stored = Intake.objects.filter(deal_id=deal_id).values_list('checklist', flat=True).first()
    entry = checklist.entry_of(stored, key)
    who = get_user_model().objects.filter(pk=entry['by']).first() if entry.get('by') else None
    return checklist.item_state(key, entry, (who.get_full_name() or who.username) if who else '')
