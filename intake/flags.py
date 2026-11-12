"""`Intake.flags`: the open warnings on a deal's shown answers, a stored count (plan.md §3.7; O.3.7, OQ9 c, Q.3 #9).

The count is `status.flags`, so it is `documents.review_rules.open_warning` (OQ28) and nothing else. Every service that
changes the answers or their sources stamps it in the same transaction (`update_answers`, the answers' Revert);
`manage.py rebuild_facts` (deals) rebuilds it through `rebuild` and reports any difference. The target effective date
counts with the other answers: its value lives on the deal (B1), its source entry here.
"""

from . import status, values


def count(deal, intake):
    from .selectors import answers_of

    answers = answers_of(deal, intake)
    return status.flags(answers, intake.sources or {}, values.hidden(answers))


def stamp(deal, intake):
    """Set `intake.flags` from its answers and sources, in memory. True when the count changed."""
    fresh = count(deal, intake)
    if fresh == intake.flags:
        return False
    intake.flags = fresh
    return True


def rebuild(deal_ids=None, write=False):
    """[(f'intake:{deal id}', stored, rebuilt)] for every Intake row whose stored count is wrong; with `write`, the
    right counts are saved (only `flags`: a rebuild changes no answer and moves no `updated_at`)."""
    from .models import Intake

    rows = Intake.objects.select_related('deal').only('deal_id', 'answers', 'sources', 'flags', 'deal__effective_date')
    if deal_ids is not None:
        rows = rows.filter(deal_id__in=deal_ids)
    wrong, differences = [], []
    for intake in rows.order_by('deal_id').iterator(chunk_size=500):
        stored = intake.flags
        if stamp(intake.deal, intake):
            differences.append((f'intake:{intake.deal_id}', stored, intake.flags))
            wrong.append(intake)
    if write and wrong:
        Intake.objects.bulk_update(wrong, ['flags'], batch_size=500)
    return differences
