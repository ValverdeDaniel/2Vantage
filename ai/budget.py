"""Budgets and limits (plan.md §10.3; D53, D99, D100, D24; slice 18).

Three caps, each on real usage:
- **a run's cap** (`AI_READ_LIMIT_USD`, $3): checked against an estimate before a read starts, from its pages and
  numbers, without an API call; past it, a read keeps what it finished and waits. Admins and direct people may Run
  anyway (D24).
- **a deal's budget** (`AI_DEAL_BUDGET_USD`, $25, or the deal's own from `DealAi`): one sum over `Job.cost_usd` (D8).
- **the total** (`AI_TOTAL_BUDGET_USD`; unset, as in production: no cap): the sum of every call this database has
  recorded, in the `Call` ledger. Every call is reserved at its worst case (its input plus every output token it may
  write, at the model's rates) under one database lock before it is sent, and refused with a sentence when that
  could pass the cap; once answered it is settled at what it used. Nothing overrides it.
"""

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Case, DecimalField, F, Sum, When

from deals import clock

from . import pricing
from .models import Call, DealAi, Job

RUN, DEAL, TOTAL = 'run', 'deal', 'total'
LEDGER_LOCK = 718_018  # pg_advisory_xact_lock key: one reservation at a time, across workers

# Estimating a read before it runs (the old claude_readers constants, D53): no API call.
CHARS_PER_TOKEN = 3.5
PAGE_INPUT_TOKENS = 2000  # a PDF page sent as a document block: its text and its picture
IMAGE_INPUT_TOKENS = 1600
NOTE_TOKENS = 400  # the per-call note outside the cache
TOKENS_PER_NUMBER = 18  # output per figure read (the old page_plan's rule)
BASE_OUTPUT_TOKENS = 300  # a range's columns, labels and structure
IMAGE_OUTPUT_TOKENS = 3000  # a page with no text layer: its figures cannot be counted
THINKING = Decimal('1.5')  # adaptive thinking at high effort writes about this much again; the trial tunes it


class OverLimit(Exception):  # noqa: N818 - the name D.6 gives it
    """A cap would be passed. `sentence` says which and by how much; `kind` is run, deal or total."""

    def __init__(self, sentence, kind):
        super().__init__(sentence)
        self.sentence = sentence
        self.kind = kind


def money(raw, default=None):
    try:
        return Decimal(str(raw)) if str(raw or '').strip() else default
    except (InvalidOperation, ValueError):
        return default


def run_cap():
    return money(settings.AI_READ_LIMIT_USD, Decimal('3'))


def total_cap():
    """The cap on everything recorded, or None (no cap)."""
    return money(getattr(settings, 'AI_TOTAL_BUDGET_USD', ''))


def deal_budget(deal_id):
    own = DealAi.objects.filter(deal_id=deal_id).values_list('budget_usd', flat=True).first()
    return own if own is not None else money(settings.AI_DEAL_BUDGET_USD, Decimal('25'))


def deal_spent(deal_id):
    return Job.objects.filter(deal_id=deal_id).aggregate(total=Sum('cost_usd'))['total'] or Decimal(0)


def ledger():
    """{'spent', 'reserved', 'calls'}: settled calls at their cost, calls still out at their worst case."""
    row = Call.objects.aggregate(
        spent=Sum(Case(When(status=Call.PENDING, then=0), default=F('cost_usd'), output_field=DecimalField())),
        reserved=Sum(Case(When(status=Call.PENDING, then=F('estimate_usd')), default=0, output_field=DecimalField())),
    )
    return {
        'spent': row['spent'] or Decimal(0),
        'reserved': row['reserved'] or Decimal(0),
        'calls': Call.objects.count(),
    }


def total_spent():
    """What the cap counts: every settled call's cost plus every unsettled call's worst case."""
    row = ledger()
    return row['spent'] + row['reserved']


def _usd(amount):
    return f'${Decimal(amount):,.2f}'


# ---- before a read -------------------------------------------------------------------------------------------------
def range_tokens(est_input, est_output):
    """(input, output) tokens one range is expected to use (ranges.Range carries its own estimates)."""
    return est_input + NOTE_TOKENS, int(est_output * THINKING)


def run_estimate(model, ranges, prompt_tokens):
    """Dollars a read of `ranges` should cost: each range's input and output, the prompt written to the cache once and
    read from it after (D53)."""
    total = Decimal(0)
    for number, part in enumerate(ranges):
        tokens_in, tokens_out = range_tokens(part.est_input, part.est_output)
        cached = (
            {'cache_read_input_tokens': prompt_tokens} if number else {'cache_creation_input_tokens': prompt_tokens}
        )
        total += pricing.cost(model, {'input_tokens': tokens_in, 'output_tokens': tokens_out, **cached})
    return total.quantize(Decimal('0.01'))


def check_run(deal_id, estimate, override=False):
    """Refuse a read whose estimate passes the run's cap or the deal's budget, unless overridden (D24)."""
    if override:
        return
    cap = run_cap()
    if estimate > cap:
        raise OverLimit(
            f'This read should cost about {_usd(estimate)}, more than the {_usd(cap)} a run may spend, so it is '
            'waiting. An admin or a direct person can run it anyway.',
            RUN,
        )
    budget, spent = deal_budget(deal_id), deal_spent(deal_id)
    if spent + estimate > budget:
        raise OverLimit(
            f'This deal has spent {_usd(spent)} of its {_usd(budget)} AI budget, and this read should cost about '
            f'{_usd(estimate)}, so it is waiting. An admin or a direct person can run it anyway.',
            DEAL,
        )


def over_run_cap(spent_this_run, override=False):
    """True once a run has really spent past its cap: it keeps what it finished and waits (D53)."""
    return not override and spent_this_run > run_cap()


# ---- each call -----------------------------------------------------------------------------------------------------
def reserve(*, model, input_tokens, max_tokens, purpose, job=None, deal_id=None):
    """The Call row for a call about to be sent, at its worst case; OverLimit (total) when that could pass the cap."""
    estimate = pricing.worst_case(model, input_tokens, max_tokens).quantize(Decimal('0.0001'))
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [LEDGER_LOCK])
        cap = total_cap()
        if cap is not None:
            spent = total_spent()
            if spent + estimate > cap:
                raise OverLimit(
                    f'Claude was not called: every Claude call here may cost {_usd(cap)} in all, {_usd(spent)} is '
                    f'spent or on its way, and this call could cost up to {_usd(estimate)}.',
                    TOTAL,
                )
        return Call.objects.create(
            job=job,
            deal_id=deal_id if deal_id is not None else getattr(job, 'deal_id', None),
            purpose=purpose,
            model=model,
            estimate_usd=estimate,
        )


def settle(call, *, answered, usage, status, stop_reason=''):
    """Record what the call used, priced from the model that answered; adds it to its job's cost. Returns the cost."""
    cost = pricing.cost(answered or call.model, usage)
    Call.objects.filter(pk=call.pk).update(
        answered=answered or '',
        usage=dict(usage or {}),
        cost_usd=cost,
        status=status,
        stop_reason=stop_reason or '',
        finished_at=clock.now(),
    )
    if call.job_id:
        Job.objects.filter(pk=call.job_id).update(cost_usd=F('cost_usd') + cost)
    return cost
