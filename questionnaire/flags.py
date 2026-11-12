"""`Questionnaire.flags`, the stored count of open warnings on the answers on screen (O.3.7, Q.3 #9): every write
rewrites it in its transaction (`services.common.restamp`); `rebuild` checks it for `manage.py rebuild_facts`."""

from .models import Questionnaire
from .selectors import context
from .services.common import view_of


def rebuild(deal_ids=None, write=False):
    """[(f'questionnaire:{id}', stored, rebuilt)] for every row whose stored count is wrong; `write` fixes them."""
    from . import values

    rows = Questionnaire.objects.select_related('deal', 'deal__client').order_by('id')
    if deal_ids is not None:
        rows = rows.filter(deal_id__in=deal_ids)
    wrong, facts = [], {}
    for row in rows:
        if row.deal_id not in facts:
            facts[row.deal_id] = context.prefill_facts(row.deal)
        view = view_of(row, facts[row.deal_id])
        rebuilt = values.flags(view.form, view.stored, view.prefill)
        if rebuilt != row.flags:
            wrong.append((f'questionnaire:{row.id}', row.flags, rebuilt))
            if write:
                Questionnaire.objects.filter(pk=row.pk).update(flags=rebuilt)
    return wrong
