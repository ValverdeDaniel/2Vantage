"""The `rank` job: ⚖ Rank plans, run by the worker in the work lane (plan.md §10.2, §10.4; D6, D36, D96, F111; slice
37; the old pipeline/advisor.py `run_rank` and `rank_case_plans` at 891f1b3).

`run(job, progress)` asks Claude once for one line: the client guidance (intake's answer and the goals the producer
recorded), the quoted plans of the line (only those the board showed, `params.plan_ids`, when it was filtered) and
how many fit on the line's proposal; Claude answers 5–8 picks with a reason each (structured output). It writes
nothing: the job's result is the picks. `land(job, result)` writes them through the star rule
(`services.rank.rank`) in the transaction that ends the job, so the stars and the job's end commit together; the job
then shows on the strip with ↶ Undo this run (the landing's one Activity row). A table locked from Claude meanwhile
(D104), or picks that no longer fit, end the job failed with the sentence, writing nothing.

A rank after a read (`params.after_read`, D96) ranks only a line nobody has chosen on yet (`rules.curated`): one
someone starred, sold or recommended on since the read is left alone, and says so in its steps.

Spending: the estimate must fit the run's cap and the deal's budget (`budget.check_run`); the call is reserved and
settled like every call. A refusal is tried once on the other of Sonnet 5.5 and Opus 5.5 for admins and direct
people (D91). Steps and errors never carry the guidance or a plan's values.
"""

from decimal import Decimal

from django.conf import settings
from django.db import transaction

from ai import budget, calls, client, kinds, pricing, reading
from ai.land import AUTO
from ai.models import DealAi, Job
from ai.progress import JobFailed
from ai.services.landing import APPLIED
from deals import activity, clock, lines

from ..selectors.state import line_state
from . import guidance, plans, prompt, rules

MAX_TOKENS = 16_000  # 5–8 short picks; adaptive thinking included
REPLY_TOKENS = 3_000  # what a rank is expected to write, for the estimate
AREAS = ['advisor', 'proposal', 'activity', 'header']

NO_PLANS = '{line} has no quoted plans to rank.'
NO_ANSWER = 'The ranking named no quoted plan of {line}, so the stars are as they were.'
LOCKED = 'The table was locked from Claude while it ranked, so no plan was starred.'
FAILED = 'Claude could not rank these plans, so the stars are as they were. {why}'
CURATED = '{line}: kept your picks ({why}); the new plans were not ranked'
LOST = 'This deal is marked lost, so the new plans were not ranked.'


def rank_key(line):
    """What names a rank's call for the fake client (ai.testing)."""
    return ('rank', line)


def _ask(job, progress, model, text):
    params = client.request(
        model=model,
        system=prompt.SYSTEM,
        content=[{'type': 'text', 'text': text}],
        schema=prompt.SCHEMA,
        effort=settings.AI_EFFORT.get('rank', 'medium'),
        max_tokens=MAX_TOKENS,
    )
    tokens = int(len(prompt.SYSTEM + text) / budget.CHARS_PER_TOKEN) + 400
    estimate = pricing.cost(model, {'input_tokens': tokens, 'output_tokens': REPLY_TOKENS})
    try:
        budget.check_run(job.deal_id, estimate)
    except budget.OverLimit as exc:
        raise JobFailed(exc.sentence) from None
    planned = calls.Planned(params, rank_key(job.params['line']), tokens)
    try:
        return calls.extract(planned, job=job, purpose='rank', on_event=progress.beat)
    except budget.OverLimit as exc:
        raise JobFailed(exc.sentence) from None


def run(job, progress):
    params = job.params or {}
    line, among = params.get('line'), params.get('plan_ids')
    if line not in lines.BY_KEY:
        raise JobFailed('This rank names no line of coverage.')
    label = lines.label(line)
    state = line_state(job.deal, line)
    if params.get('after_read'):
        why = rules.curated(state.data)
        if why or job.deal.stage == 'lost':
            progress.step(LOST if not why else CURATED.format(line=label, why=why), 100)
            return {'v': 1, 'target': 'rank', 'line': line, 'picks': [], 'skipped': why or 'lost'}
    words = guidance.block(job.deal)  # JobFailed when it was emptied since the button was pressed
    ids = rules.scope(state.data, among)
    listed = plans.plan_lines(job.deal, line, ids)
    if not listed:
        raise JobFailed(NO_PLANS.format(line=label))
    fit = rules.fit(state.data, ids)
    count = len(listed)
    progress.step(f'Scoring {count} {label} plan{"s" if count != 1 else ""} against the client guidance', 20)
    text = prompt.content(line, words, listed, fit, among is not None)
    model = reading.model_for(job)
    done = _ask(job, progress, model, text)
    spent = Decimal(done.cost or 0)
    other = pricing.other_model(model)
    if isinstance(done.error, client.Refused) and other and job.created_by and reading.may_use_opus(job.created_by):
        model = other
        done = _ask(job, progress, model, text)
        spent += Decimal(done.cost or 0)
    Job.objects.filter(pk=job.pk).update(model=model)
    if done.error is not None:
        raise JobFailed(FAILED.format(why=done.error.sentence))
    picks = rules.picks_from(done.data)
    chosen, _left = rules.choose(state.data, picks, ids)
    if not chosen:
        raise JobFailed(NO_ANSWER.format(line=label))
    progress.step('Starring the plans that fit best', 95)
    return {
        'v': 1,
        'target': 'rank',
        'line': line,
        'among': among,
        'picks': [{'plan': plan_id, 'reason': why} for plan_id, why in picks],
        'summary': f'Ranked the {label} plans',
        'counts': {'picks': len(chosen)},
        'model': model,
        'cost_usd': f'{spent:.4f}',
    }


def land(job, result):
    """The fields a finished rank ends with: its stars written ({land: auto, resolution: applied, result with
    `landed`, activity}), or failed with the sentence when they cannot be written now."""
    from ..services.rank import rank

    picks = [(pick['plan'], pick['reason']) for pick in (result or {}).get('picks') or []]
    if not picks:
        return {}
    if DealAi.objects.filter(deal_id=job.deal_id, locked_at__isnull=False).exists():
        return {'status': kinds.FAILED, 'error': LOCKED}
    try:
        with transaction.atomic():  # a savepoint: a refusal goes back alone, the job still ends
            ranked = rank(job.created_by, job.deal, result['line'], picks, result.get('among'))
    except activity.Refused as exc:
        return {'status': kinds.FAILED, 'error': exc.sentence[:300]}
    label, count = lines.label(result['line']), len(ranked.starred)
    summary = f'starred {count} {label} plan{"s" if count != 1 else ""}'
    skipped = []
    if ranked.left_out:
        left = len(ranked.left_out)
        skipped.append(f'{left} more {"was" if left == 1 else "were"} left out: the {label} proposal is full.')
    landed = {
        'activity_id': ranked.row.id if ranked.row else None,
        'activity_ids': [ranked.row.id] if ranked.row else [],
        'plan_ids': ranked.starred,
        'areas': AREAS if ranked.row else [],
        'summary': summary,
        'skipped': skipped,
        'line': result['line'],
        'by': getattr(job.created_by, 'id', None),
        'at': clock.now().isoformat(),
        'auto': True,
    }
    return {
        'land': AUTO,
        'resolution': APPLIED,
        'result': {**result, 'landed': landed},
        'activity_id': landed['activity_id'],
    }
