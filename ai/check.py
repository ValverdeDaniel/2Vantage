"""The `locate` job: "Check this file" (plan.md §10.7; E59, E81–E84, D95, D-122; the old benefits/ai/source_check.py).

For each file, every value owner (registry.locate_hooks) names the values that came from it and how to look for each
one; the locator (documents.locate) reads the file once and answers where each value is printed, or that it is not;
each owner stores the answers as the values' `loc` (deals.values.set_loc). What it promises, as the old check did:
- it never changes a value, a mark or an approval: the check raises doubt and never approves;
- it is idempotent: without `recheck` only values never checked (or checked by an older locator) are looked for, and
  an answer equal to the stored one writes nothing;
- it names files by id and counts in steps, results and Activity, never a file name or a value.
It runs in the system lane, so it never waits behind a read (E59). A file done is kept when Stop is pressed.
"""

from collections import Counter

from django.db import transaction

from deals import activity, clock
from documents import locate
from documents.models import Document

from . import kinds, registry
from .progress import Progress

COUNTED = (locate.FOUND, locate.DERIVED, locate.WEAK, locate.ABSENT, locate.NOCHECK)


def _bytes(document):
    try:
        with document.file.open('rb') as handle:
            return handle.read()
    except (FileNotFoundError, OSError, ValueError):
        return None


def queries(deal, document, recheck):
    """[(owner, ref, query)] for every owner's values that name this file."""
    return [
        (owner, ref, query)
        for owner, hook in registry.locate_hooks.items()
        for ref, query in hook.queries(deal, document, recheck)
    ]


def _summary(counts):
    checked = counts['checked']
    if not checked:
        return 'nothing left to check'
    noun = 'value' if checked == 1 else 'values'
    absent = counts[locate.ABSENT]
    return f'Checked {checked} {noun} against the file' + (f' — {absent} not found in it' if absent else '')


def _save(user, deal, document, items, results):
    """Each owner stores its answers; one Activity row (counts only) when any answer was stored. One transaction."""
    stamp = {'v': locate.VERSION, 'at': clock.now().isoformat()}
    by_owner = {}
    for (owner, ref, _query), result in zip(items, results, strict=True):
        by_owner.setdefault(owner, []).append((ref, {**result.as_dict(), **stamp}))
    counts = Counter(result.state for result in results)
    counts['checked'] = len(results)
    saved, areas, row = 0, set(), None
    with transaction.atomic():
        for owner, answers in by_owner.items():
            outcome = registry.locate_hooks[owner].save(user, deal, document, answers)
            saved += outcome['saved']
            areas.update(outcome.get('areas', ()))
        if saved:
            row = activity.record(deal, user, 'ai', 'checked', _summary(counts), document_id=document.id)
    return counts, saved, areas, row


def check_document(user, deal, document, recheck=False, progress=None, span=(0, 100), where=''):
    """Look for every value this file holds (or only the unchecked ones) and store what was found. Returns
    (counts, saved, areas, activity row or None). `where` names the file in the job's lines ("File 2 of 6")."""
    items = queries(deal, document, recheck)
    if not items:
        return Counter(checked=0), 0, set(), None
    low, high = span

    def line(text):
        return f'{where}: {text}' if where else text[0].upper() + text[1:]

    def on_page(number, total):
        if progress:
            progress.say(line(f'reading page {number:,} of {total:,}'), low + (high - low) * 0.9 * number / total)

    raw = _bytes(document)
    if raw is None:
        index, why = None, 'missing'
    else:
        index, why = locate.open_index(document.original_name, raw, document.page_count, on_page)
    if progress:
        noun = 'value' if len(items) == 1 else 'values'
        progress.say(line(f'looking for {len(items):,} {noun}'), low + (high - low) * 0.95)
    results = locate.locate_all(index, why, [query for _owner, _ref, query in items])
    return _save(user, deal, document, items, results)


def _file_line(position, total):
    return f'File {position} of {total}' if total > 1 else 'The file'


def run(job, progress: Progress):
    """The `locate` job's runner: the job's files in order; returns the result (counts, files, landed areas)."""
    recheck = bool((job.params or {}).get('recheck'))
    found = {doc.id: doc for doc in Document.all_objects.filter(deal_id=job.deal_id, pk__in=job.documents)}
    files = [found[doc_id] for doc_id in job.documents if doc_id in found]
    totals, areas, per_file, saved = Counter(), set(), [], 0
    progress.step('Checking the values against their file' + ('s' if len(files) > 1 else ''))
    for position, document in enumerate(files, start=1):
        span = (100 * (position - 1) / len(files), 100 * position / len(files))
        where = _file_line(position, len(files)) if len(files) > 1 else ''
        counts, stored, landed, row = check_document(job.created_by, job.deal, document, recheck, progress, span, where)
        totals.update(counts)
        saved += stored
        areas |= landed
        if row is not None:
            progress.activity_id = row.id
        per_file.append({'id': document.id, 'checked': counts['checked'], 'absent': counts[locate.ABSENT]})
        progress.result = _result(totals, per_file, saved, areas)
        progress.step(f'{_file_line(position, len(files))}: {_summary(Counter(counts))}', span[1])
    return progress.result or _result(totals, per_file, saved, areas)


def _result(totals, per_file, saved, areas):
    return {
        'counts': {'checked': totals['checked'], **{state: totals[state] for state in COUNTED}},
        'files': per_file,
        'saved': saved,
        'landed': {'areas': sorted(areas), 'plan_ids': []},
    }


def register():
    registry.register_kind(kinds.LOCATE, run)
