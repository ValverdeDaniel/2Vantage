"""The Overview's data confidence (plan.md §8.6, §7.13; M83, M86, M87, M90, M91, M92; M.6 `review.selectors.confidence`;
the old serializers/overview.py `confidence_payload` at 891f1b3; slice 64): where every stored value on the deal came
from, and whether a person has checked it. `GET deals/{id}/confidence/`.

Every owner (intake, census, quotes, the questionnaires) counts its own `sources` in SQL (`<owner>.confidence`, one
aggregate each over `jsonb_each(sources)`), and the counts are folded here through the one set of review rules
(`documents.review_rules`): `origin_bucket` puts each value in a cell, `is_approved` and the approval's `via` in the
confirmed bar, `open_warning` and the marks in the warnings. So the read costs a fixed number of queries at any size
(B24, Q.7), and the Overview, the Advisor and the station agree (OQ28).

- `cells`: Scanned (Claude read it, with "N corrected by hand": typed over a read value, keeping its file), Typed,
  From the client (approved answers), and the client's answers still waiting for approval (`pending`).
- `confirmed`: approvals out of the stored values — by a person, or by a person applying Claude's re-check (M86).
- `warnings`: Claude unsure (`low`), open warnings (`to_review`), ⚑ Needs checking (`check`), Ignored.
- `documents`: per file its values, how many are confirmed and its quality headline (M87; high = its clean values, low
  = its open warnings), most values first, 50 at most plus `more`.
- `ignored` / `check`: the marked values newest first, 50 each plus `more` (M90, M91): where, the field, the value —
  never for census, questionnaires or lasers (`value: None`, §3.8) — the file, who and when.
- `recheck`: how many values the AI re-read would take, and the last re-check (M92), with its first six differences.
Reads only: nothing is written, not even a row (§3.6).
"""

from decimal import Decimal

from django.contrib.auth import get_user_model

from ai import kinds
from ai.models import Job
from ai.services.landing import waiting as is_waiting
from census import confidence as census_side
from census import facts as census_facts
from documents import review_rules as rules
from documents.models import Document
from documents.source_counts import entry
from intake import confidence as intake_side
from questionnaire import confidence as questionnaire_side
from quotes import confidence as quote_side
from quotes.math import round_decimal

from . import entries as client_entries

SIDES = (intake_side, census_side, quote_side, questionnaire_side)  # chain order
CAP = 50  # rows a list shows; the rest is `more` (the old MARKED_LIST_CAP)
DIFFERENCES = 6  # the re-check's differences shown (the old panel's first six)
REMOVED = 'Removed document'
CELL = {'scanned': 'scanned', 'corrected': 'scanned', 'client': 'from_client', 'typed': 'typed'}  # origin_bucket's


def _cells():
    return {'scanned': 0, 'corrected': 0, 'typed': 0, 'from_client': 0, 'pending': 0}


def _doc():
    return {'values': 0, 'confirmed': 0, 'to_review': 0, 'check': 0, 'ignored': 0}


def _fold(groups):
    cells, docs = _cells(), {}
    filled = by_person = by_recheck = low = to_review = check = ignored = 0
    for group in groups:
        value, n = entry(group), group.count
        bucket = rules.origin_bucket(value)
        cells[CELL.get(bucket, 'typed')] += n
        cells['corrected'] += n if bucket == 'corrected' else 0  # also counted as scanned: "N corrected by hand"
        filled += n
        approved, warning, state = rules.is_approved(value), rules.open_warning(value), rules.mark_state(value)
        if approved and group.via == 'recheck':
            by_recheck += n
        elif approved:
            by_person += n
        low += n if group.low and group.origin == rules.READ else 0  # Claude was unsure (M86's "low-confidence")
        to_review += n if warning else 0
        check += n if state == rules.CHECKING else 0
        ignored += n if state == rules.IGNORED else 0
        if group.doc:
            doc = docs.setdefault(group.doc, _doc())
            doc['values'] += n
            doc['confirmed'] += n if approved else 0
            doc['to_review'] += n if warning else 0
            doc['check'] += n if state == rules.CHECKING else 0
            doc['ignored'] += n if state == rules.IGNORED else 0
    confirmed = by_person + by_recheck
    pct = int(round_decimal(Decimal(confirmed * 100) / filled)) if filled else 0
    return {
        'cells': cells,
        'filled': filled,
        'confirmed': {'total': confirmed, 'by_person': by_person, 'by_recheck': by_recheck, 'pct': pct},
        'warnings': {'low': low, 'to_review': to_review, 'check': check, 'ignored': ignored},
    }, docs


def _pending(deal):
    """The client's answers waiting for approval: intake's and the forms' entries, census's stored count."""
    found = client_entries.waiting([deal.id], ('intake', 'questionnaire')).get(deal.id, [])
    return len(found) + census_facts.stored(deal.id).get('pending_answers', 0)


def _names(ids):
    users = get_user_model().objects.filter(id__in=sorted(ids) or [0])  # one query; 0 is never a user id
    return {user.id: user.get_full_name() or user.username for user in users}


def _files(deal, ids):
    found = Document.all_objects.filter(deal=deal, id__in=sorted(ids) or [0]).only('id', 'original_name', 'kind')
    return {doc.id: {'id': doc.id, 'name': doc.original_name, 'kind': doc.kind} for doc in found}


def _file(files, doc_id):
    if not doc_id:
        return None
    return files.get(doc_id) or {'id': doc_id, 'name': REMOVED, 'kind': ''}


def _marked(rows, state):
    """One list's rows, newest first (the marks' own stamps; ties by the owners' order), the first CAP of them."""
    mine = [row for row in rows if row['state'] == state]
    return sorted(mine, key=lambda row: row['at'] or '', reverse=True)[:CAP]


def _row(row, files, names):
    out = {key: row[key] for key in ('ref', 'owner', 'where', 'label', 'value', 'tab', 'at')}
    out.update(form=row.get('form'), doc=_file(files, row['doc']), by=names.get(row['by'], ''))
    return out


def _last_recheck(job, files):
    if job is None:
        return None
    result = job.result or {}
    counts = result.get('counts') or {}
    differ = [item for item in result.get('items') or [] if item.get('op') == 'set_values']
    shown = []
    for item in differ[:DIFFERENCES]:
        value = (item.get('values') or [{}])[0]
        plan = ' '.join(part for part in (item.get('carrier'), item.get('name')) if part)
        shown.append(
            {
                'label': f'{plan} — {value.get("label", "")}' if plan else value.get('label', ''),
                'old': value.get('old'),
                'new': value.get('new'),
                'doc': _file(files, value.get('doc')),
                'page': value.get('page'),
            }
        )
    agreed, fixes, unverified = counts.get('approvals', 0), counts.get('fixes', 0), counts.get('unverified', 0)
    return {
        'job_id': job.id,
        'status': job.status,
        'scanned': bool((job.params or {}).get('scanned')),
        'waiting': is_waiting(job),
        'resolution': job.resolution,
        'error': job.error,
        'at': job.finished_at or job.created_at,
        'counts': {'checked': agreed + fixes + unverified, 'agreed': agreed, 'differ': fixes, 'not_found': unverified},
        'differences': shown,
    }


def _recheck_docs(job):
    items = ((job.result or {}).get('items') or []) if job else []
    return {(item.get('values') or [{}])[0].get('doc') for item in items if item.get('op') == 'set_values'} - {None}


def confidence(deal):
    groups = {side.OWNER: side.source_counts(deal.id) for side in SIDES}
    head, docs = _fold([group for found in groups.values() for group in found])
    head['cells']['pending'] = _pending(deal)
    rows = [row for side in SIDES for row in side.marked(deal.id, CAP)]
    lists = {state: _marked(rows, state) for state in (rules.IGNORED, rules.CHECKING)}
    job = Job.objects.filter(deal=deal, kind=kinds.RECHECK).order_by('-id').first()
    ordered = sorted(docs.items(), key=lambda item: (-item[1]['values'], item[0]))
    shown = ordered[:CAP]
    wanted = {doc_id for doc_id, _counts in shown} | {row['doc'] for found in lists.values() for row in found}
    files = _files(deal, (wanted | _recheck_docs(job)) - {None})
    names = _names({row['by'] for found in lists.values() for row in found} - {None})
    documents = []
    for doc_id, counts in shown:
        high, low = counts['values'] - counts['to_review'], counts['to_review']
        documents.append({**_file(files, doc_id), **counts, 'headline': rules.quality_headline(high, low, 0)})
    documents.sort(key=lambda doc: (-doc['values'], doc['name'].lower(), doc['id']))
    totals = head['warnings']
    takes = sum(group.count for group in groups[quote_side.OWNER] if group.doc and not group.confirmed)
    return {
        'deal_id': deal.id,
        **head,
        'documents': documents,
        'documents_more': len(ordered) - len(shown),
        'ignored': {'rows': [_row(row, files, names) for row in lists[rules.IGNORED]],
                    'more': max(0, totals['ignored'] - len(lists[rules.IGNORED]))},
        'check': {'rows': [_row(row, files, names) for row in lists[rules.CHECKING]],
                  'more': max(0, totals['check'] - len(lists[rules.CHECKING]))},
        'recheck': {'values': takes, 'last': _last_recheck(job, files)},
    }  # fmt: skip
