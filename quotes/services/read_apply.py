"""Using a quote read (plan.md §10.5; D67, D72, D75, D56, D115, D117; slice 19): "Use this scan ▸" or "Apply N
selected ▸" on the review card lands the chosen parts of a read's change set through the owners' own writers, in one
transaction that locks the Deal first, then the lines' plans by id (O.3.7):

1. lines the deal does not ask for yet (D56) through Intake's `set_intent`, its own Activity row (intake owns them);
2. the plans and values (`read_plans.Landing`), recorded as ONE Activity row (area `quote_read`), with before and after
   per key and a `plan.read_ref` key on each plan the read made, which Undo reads (`revert_read`);
   The same row records the file's printed tables (`layouts.write`, D66; slice 21): each file and line's columns as
   the plans they landed on and its rows in printed order, so "As quoted" shows the quote as printed;
3. the printed tier counts a person ticked (D67, OQ30) through `set_enrollment`, the one writer of typed counts: they
   become the plans' (or the line's) typed counts and price them; its own row (area `enrollment`);
4. the deal moves forward to Quoting (D75; `deals.services.advance`, forward only, its own row), when a plan, a value
   or a count landed.
First of all, the files' printed page numbers the read found (E94) are kept on the documents (`set_page_labels`).
Every row but the stage's is the landing's: the job keeps their ids, and ↶ Undo this run reverts them together
(`revert_read.undo`). Nothing chosen that still differs from the deal writes nothing: no plan, no Activity, no stage.

Returns the `landed` record the job keeps: what changed (plan ids, the areas to refetch), the main Activity row, every
row of the landing, the source entries the landed values replaced (so Undo can put a read value back as read), the
printed tables the landing replaced (`layouts`, for Undo), and sentences for what was left out and why.
"""

from django.db import transaction

from deals import activity
from deals import lines as line_vocab
from deals.services import advance
from documents.services import set_page_labels
from intake.services import intent

from .. import signals
from ..reader import choice
from . import layouts, locks
from .enrollment import set_enrollment
from .read_plans import Landing

AREA, ACTION = 'quote_read', 'read'
REASON = 'a quote read landed'
AREAS = ['advisor', 'review', 'activity', 'header', 'proposal', 'documents', 'intake']
NOTHING = 'Nothing changed: what this read found is already on the deal.'
TABLE = 'the file’s printed table'
COUNTS_GONE = 'the plan these counts are for was not added, so they were left out.'


def _add_lines(user, deal, entries):
    wanted = []
    for entry in entries:
        wanted += [line for line in entry.item.get('lines') or [] if line in line_vocab.BY_KEY and line not in wanted]
    if not wanted:
        return None
    return intent.set_intent(user, deal.id, lines=wanted, shop=True).activity


def _counts(user, deal, landing, entries):
    """Write the ticked printed counts as typed counts, one `set_enrollment` per line; (rows, words)."""
    by_line = {}
    for entry in entries:
        by_line.setdefault(entry.item['line'], []).append(entry.item)
    rows, plans_counted, lines_counted = [], 0, 0
    for line, items in by_line.items():
        per_plan, figure = None, None
        for item in items:
            if item.get('for') is None:
                figure = dict(item['counts'])
                continue
            plan = landing.resolve(item['for'])
            if plan is None or plan.line != line:
                landing.skipped.append(f'{item["label"]}: {COUNTS_GONE}')
                continue
            if per_plan is None:
                per_plan = {p.id: dict(p.enrollment or {}) for p in landing.rows.values() if p.line == line}
            per_plan[plan.id] = dict(item['counts'])
        kwargs = {}
        if per_plan is not None:
            kwargs['plans'] = [{'id': pid, 'enrollment': counts} for pid, counts in per_plan.items() if counts]
        if figure is not None:
            kwargs['whole_line'] = figure
        if not kwargs:
            continue
        saved = set_enrollment(user, deal, line, on=True, **kwargs)
        if saved.activity is not None:
            rows.append(saved.activity)
            plans_counted += len({plan.id for plan in saved.plans})
            lines_counted += 1 if saved.line is not None and figure is not None else 0
    words = []
    if plans_counted:
        words.append(f'counts on {plans_counted} plan{"s" if plans_counted != 1 else ""}')
    if lines_counted:
        words.append('the line’s counts')
    return rows, words


@transaction.atomic
def apply(user, deal, job, select=None, picks=None):
    """Land the chosen parts of `job`'s change set (`choice.choose`); returns the `landed` record."""
    change_set = job.result or {}
    chosen = choice.choose(change_set, select, picks)
    deal = locks.deal(deal.id)
    for document_id, labels in (change_set.get('page_labels') or {}).items():  # documents' rows first (the lock order)
        set_page_labels(int(document_id), deal, labels)
    lines_row = _add_lines(user, deal, choice.of_op(chosen, 'add_lines'))
    plan_entries = choice.plan_items(chosen)
    count_entries = choice.of_op(chosen, 'summary_counts')
    line_keys = {entry.item['line'] for entry in [*plan_entries, *count_entries]}
    landing = Landing(user, deal, locks.lines(deal, line_keys) if line_keys else {}, job)
    for entry in plan_entries:
        landing.land(entry)
    landing.place()
    entries = landing.entries()
    landed = {item_id: plan.id for item_id, plan in landing.by_item.items()}
    table_entries, replaced = layouts.write(deal, job, change_set, landed)
    words = landing.words()
    main = None
    if entries or table_entries:
        documents = change_set.get('documents') or []
        main = activity.record(
            deal,
            user,
            AREA,
            ACTION,
            f'Used Claude’s read: {words or ("values on the plans" if entries else TABLE)}',
            changes=entries + table_entries,
            document_id=documents[0] if documents else None,
        )
    if entries:
        signals.changed(deal.id, {landing.rows[int(entry['t'].partition(':')[2])].line for entry in entries})
    count_rows, count_words = _counts(user, deal, landing, count_entries)
    rows = [row for row in (lines_row, main, *count_rows) if row is not None]
    if entries or count_rows:
        advance(deal, user, 'quoting', REASON)
    said = ' · '.join(part for part in [words, *count_words] if part)
    if lines_row is not None:
        said = ' · '.join(part for part in [said, 'lines added'] if part)
    if table_entries and not said:
        said = TABLE
    return {
        'activity_id': (main or (rows[0] if rows else None)).id if rows else None,
        'activity_ids': [row.id for row in rows],
        'plan_ids': sorted({*landing.diffs, *(p.id for p in landing.created)}),
        'created': [plan.id for plan in landing.created],
        'areas': AREAS if rows else [],
        'summary': said or NOTHING,
        'skipped': landing.skipped,
        'sources': landing.sources,
        'layouts': replaced,
    }
