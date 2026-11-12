"""The go-to-market gate of one deal (plan.md §5.2, §7.6; B13, B25–B35): what the Intake tab, Mark as marketed and the
summary read beside the form — the client's contacts, the BOR, the compliance files, the marketing checklist with its
tier, and the ready state with its gaps. Reads only: the providers answer the headcount, Census OK and the
questionnaire forms (O.1); nothing is created by a read.
"""

from django.contrib.auth import get_user_model

from deals import contacts as roles
from deals.models import Contact
from deals.selectors import contact_row
from documents.models import Document
from documents.review_rules import open_warning

from . import checklist, checklist_words, form, providers, readiness
from .values import blank


def documents_of(deal_id):
    """The deal's files that count, as (id, kind, lines, name): live ones, less a file a person marked the wrong one
    (it answers nothing, as the old checklist's `document_rows`) and a copy the app filed itself (a signed form's,
    G135): the checklist reads a form's own signature, so a reopened form is not done by its earlier copy."""
    found = (
        Document.objects.filter(deal_id=deal_id, protected=False)
        .exclude(review_state='wrong')
        .order_by('id')
        .values_list('id', 'kind', 'lines', 'label', 'original_name')
    )
    return [(doc_id, kind, lines, label or name) for doc_id, kind, lines, label, name in found]


def contacts_of(deal):
    return list(Contact.objects.filter(client_id=deal.client_id).order_by('sort_order', 'id'))


def _names(ids):
    wanted = {pk for pk in ids if pk}
    if not wanted:
        return {}
    users = get_user_model().objects.filter(pk__in=wanted)
    return {user.id: user.get_full_name() or user.username for user in users}


def _fundings(rows, quote_lines):
    """Every funding the deal records: its coverage rows' and its current plans' (claims reads them, B26)."""
    found = {row.funding for row in rows if row.funding}
    found |= {(line.get('current') or {}).get('funding') for line in quote_lines.values()}
    return {funding for funding in found if funding}


def question_gaps(answers, sources, needed):
    """([(key, label)] blank, [(key, label)] answered with an open warning) over the needed questions."""
    missing, to_check = [], []
    for key in needed:
        label = form.BY_KEY[key]['label']
        if blank(answers.get(key)):
            missing.append((key, label))
        elif open_warning((sources or {}).get(key)):
            to_check.append((key, label))
    return missing, to_check


def _bor(intake, documents, names):
    signed_at = intake.bor_signed_at if intake else None
    files = [{'id': doc_id, 'name': name} for doc_id, kind, _lines, name in documents if kind == 'bor']
    by = intake.bor_signed_by_id if intake else None
    return {
        'name': intake.bor_name if intake and signed_at else '',
        'signed_at': signed_at,
        'signed_by': by if signed_at else None,
        'by_name': names.get(by, '') if signed_at else '',
        'files': files,
        'on_file': readiness.bor_on_file(signed_at, files),
    }


def _compliance(documents):
    return [
        {
            'kind': kind,
            'label': label,
            'documents': [{'id': doc_id, 'name': name} for doc_id, found, _lines, name in documents if found == kind],
        }
        for kind, label in checklist_words.COMPLIANCE
    ]


def read(deal, intake, *, rows, quote_lines, intent, documents, answers, needed, contacts, issues=None):
    """The gate's blocks for the intake payload: {contacts, primary_id, contacts_ok, bor, compliance, checklist, ready,
    marketed}. `intent` is the coverage card; `answers` the shown answers; `needed` the needed questions."""
    stored = (intake.checklist if intake else None) or {}
    ticks = [entry.get('by') for entry in stored.values() if isinstance(entry, dict)]
    names = _names([*ticks, intake.bor_signed_by_id if intake else None, intake.marketed_by_id if intake else None])
    headcount = providers.headcount(deal.id)
    census_ok = bool(providers.census_state(deal.id).get('ok'))
    facts = checklist.Facts(
        headcount=headcount.get('count'),
        census_ok=census_ok,
        intent=intent,
        requested_lines=deal.requested_lines,
        kinds={kind for _id, kind, _lines, _name in documents},
        funding=_fundings(rows, quote_lines),
        self_funded=answers.get('self_funded') or '',
        forms=providers.questionnaire_items(deal.id),
        stored=stored,
    )
    card = checklist.card(facts, headcount)
    for row in card['items']:
        row['by_name'] = names.get(row['by'], '') if row['attested'] else ''
    bor = _bor(intake, documents, names)
    ok = readiness.contacts_ok(contacts)
    missing, to_check = question_gaps(answers, intake.sources if intake else {}, needed)
    marketed_at = intake.marketed_at if intake else None
    main = roles.primary(contacts)
    return {
        'contacts': [{**contact_row(c), 'issues': (issues or {}).get(f'contact:{c.id}', [])} for c in contacts],
        'primary_id': main.id if main else None,
        'contacts_ok': ok,
        'bor': bor,
        'compliance': _compliance(documents),
        'checklist': card,
        'ready': readiness.ready(
            marketed_at=marketed_at,
            contacts_ok=ok,
            bor_on_file=bor['on_file'],
            census_ok=census_ok,
            missing=missing,
            to_check=to_check,
            items=card['items'],
        ),
        'marketed': {
            'at': marketed_at,
            'by': intake.marketed_by_id,
            'by_name': names.get(intake.marketed_by_id, ''),
        }
        if marketed_at
        else None,
    }
