"""Starting a rank (plan.md §7.5 `deals/{id}/ai/rank/`, §10.4; D6, D96, F111, OQ44; slice 37).

- `start_rank(user, deal, line, plan_ids=None, model='')` is ⚖ Rank plans (and "⚖ Rank filtered (N)" with the ids the
  board shows), and Claude's `rank_plans`: one `rank` job on the work lane, for one line (F111: Rank needs a line;
  the old Rank without one ranked every line together). Refused with a sentence: without Claude (D26), without client
  guidance ("Add client guidance first"), with the table locked from Claude (D104: Rank stars plans), with Opus asked
  by someone neither admin nor direct (D91), or with no quoted plan to rank; 400 for a line or ids that are not the
  deal's. The same rank already going is returned (`ai.services.start`).
- `after_read(user, deal, job, landed)`: when a quote read lands (by itself or used by a person), each line it added
  quoted plans to is ranked, once the read commits, when the deal has guidance and nobody has chosen on that line
  yet: no star, no sale, no recommendation (D96; the old R5 `rank_after_read`). A line someone curated keeps its
  picks; a lost deal ranks nothing.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from ai import client, kinds, pricing, reading
from ai.models import DealAi
from deals import lines
from deals.activity import Refused

from ..models import Plan
from ..selectors.state import line_state
from . import guidance, rules

NO_KEY = 'Claude is not set up on this server, so nothing can be ranked.'
LOCKED = 'The table is locked from Claude, so it cannot star plans. Unlock it to rank.'
NO_OPUS = 'Opus 5.5 is kept to admins and direct people.'
NO_PLANS = '{line} has no quoted plans to rank.'
NOT_HERE = 'Those plans are not quoted plans of that line on this deal.'


def start_rank(user, deal, line, *, plan_ids=None, model='', after_read=None):
    """(job, created)."""
    from ai.services import start

    if not client.available():
        raise Refused(NO_KEY)
    if line not in lines.BY_KEY:
        raise ValidationError({'line': ['Give a line of coverage.']})
    if not guidance.written(deal):
        raise Refused(guidance.NO_GUIDANCE)
    if DealAi.objects.filter(deal=deal, locked_at__isnull=False).exists():
        raise Refused(LOCKED)
    if model and (model not in pricing.READ_MODELS or (model == pricing.OPUS and not reading.may_use_opus(user))):
        raise Refused(NO_OPUS)
    roles = dict(Plan.objects.filter(deal=deal, line=line).values_list('id', 'role'))
    quoted = {plan_id for plan_id, role in roles.items() if role != 'current'}
    params = {'line': line}
    if plan_ids is not None:
        among = sorted(set(plan_ids))
        if not set(among) <= set(roles):
            raise ValidationError({'plan_ids': [NOT_HERE]})
        quoted &= set(among)
        params['plan_ids'] = among
    if not quoted:
        raise Refused(NO_PLANS.format(line=lines.label(line)))
    if model:
        params['model'] = model
    if after_read:
        params['after_read'] = int(after_read)
    return start(user, deal, kinds.RANK, params=params)


def _start_after(user, deal_id, read_id, line_keys):
    from deals.models import Deal

    deal = Deal.objects.filter(pk=deal_id).first()
    if deal is None or deal.stage == 'lost' or not client.available() or not guidance.written(deal):
        return
    for line in line_keys:
        if rules.curated(line_state(deal, line).data):
            continue
        try:
            start_rank(user, deal, line, after_read=read_id)
        except (Refused, ValidationError):
            continue  # locked meanwhile, or the plans went: the read stays as it landed


def after_read(user, deal, job, landed):
    """Queue the rank after a quote read, on commit (the read and its landing come first)."""
    created = (landed or {}).get('created') or []
    if not created or not guidance.written(deal):
        return
    found = Plan.objects.filter(deal=deal, pk__in=created).exclude(role='current').values_list('line', flat=True)
    line_keys = [key for key in lines.LINE_KEYS if key in set(found)]
    if line_keys:
        transaction.on_commit(lambda: _start_after(user, deal.id, job.id, line_keys))
