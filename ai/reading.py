"""Every reader runs through here (plan.md §10.4; D46, D48–D51, D53, D64, D65, E79; slice 18).

A `read` job's files go in upload order: screen → ranges (`ranges.py`) → an estimate that stops at the cap → content
(`content.py`) → `extract`, up to four ranges at once, halving a range whose answer is cut off → the reader merges the
answers, finds each value in its file and builds the change set (D.6's shape) → when the read found something it
doubts hard and its person may use Opus 5.5, Opus reads the files again and its read replaces the first (D76's
step-up, before landing) → the change set lands by itself or waits for review (`ai/land.py`, D71; the job's land hook,
`services.landing.on_finish`). Nothing here writes a plan, a value or Activity: the job's own row holds the change
set, and each call its row in the ledger.

What a read keeps when it ends early: Stop keeps the ranges finished (the change set is marked partial); a run past its
cost cap, or one the total cap or the account refuses, keeps them too and names the rest as failed parts. A run whose
estimate passes its cap or the deal's budget waits before it starts, unless overridden (D24). Steps, errors and the
change set never carry a file name or a file's text.
"""

import json
from collections import deque
from decimal import Decimal

from django.conf import settings

from accounts.access import can_direct
from documents.models import Document

from . import budget, calls, carrier_notes, client, content, pricing, ranges, read_files, registry
from .models import Job
from .progress import JobFailed, Stopped

USAGE_KEYS = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
OVER_BUDGET, STAGED = 'budget', 'staged'  # Job.land: waiting past a cap; waiting for review (land.py: auto)
HALTS = {budget.TOTAL: 'total_cap', budget.RUN: 'over_cap'}
STEP_UP = 'Claude doubted part of this read, so Opus 5.5 reads it again'
STEP_UP_FAILED = 'Opus 5.5 could not finish reading these files again, so this is the first read.'


def may_use_opus(user):
    """Opus 5.5 is for admins and direct people (D91)."""
    return bool(getattr(user, 'is_staff', False)) or can_direct(user)


def model_for(job):
    asked = (job.params or {}).get('model') or settings.AI_MODEL
    return asked if asked in pricing.READ_MODELS else settings.AI_MODEL


def prompt_tokens(reader):
    return int(len(reader.prompt + json.dumps(reader.schema)) / budget.CHARS_PER_TOKEN)


def planned_call(reader, file, part, note, *, model, effort):
    params = client.request(
        model=model,
        system=reader.prompt,
        content=content.blocks(file, part, note),
        schema=reader.schema,
        effort=effort,
    )
    tokens_in, _ = budget.range_tokens(part.est_input, part.est_output)
    return calls.Planned(
        params, (reader.target, file.hash, part.label), tokens_in + prompt_tokens(reader), (file, part)
    )


class Run:
    """One read's state while its calls run: what finished, what failed, what it cost."""

    def __init__(self, job, progress, reader, files, *, model, effort):
        self.job, self.progress, self.reader, self.files = job, progress, reader, files
        self.model, self.effort = model, effort
        self.override = bool((job.params or {}).get('budget_override'))
        self.allow_other = may_use_opus(job.created_by)
        self.parts, self.failed, self.findings = [], [], []
        self.spent, self.usage, self.calls = Decimal(0), dict.fromkeys(USAGE_KEYS, 0), 0
        self.halt = None  # (reason, sentence) once the run stops launching calls
        self.total = 0
        self.notes = {}

    def note(self, file):
        """The per-call note, outside the cache: the reader's own, then the file's carrier note (D55, D119)."""
        if file.id not in self.notes:
            note = self.reader.note(file, {'deal_lines': list(self.job.deal.requested_lines or [])})
            self.notes[file.id] = carrier_notes.note_for_read(note, file.carrier)
        return self.notes[file.id]

    def fail(self, file, part, reason):
        self.failed.append({'doc': file.id, 'where': part.where(), 'reason': reason, 'pages': list(part.pages)})

    def record(self, done):
        self.calls += 1
        self.spent += Decimal(done.cost or 0)
        for key in USAGE_KEYS:
            self.usage[key] += int(((done.reply.usage if done.reply else {}) or {}).get(key) or 0)

    def handle(self, done, queue):
        file, part = done.planned.tag
        self.record(done)
        error = done.error
        halves = ranges.halve(part) if isinstance(error, client.Truncated) else None
        if error is None:
            self.parts.append((file, part, done.data))
        elif halves:
            queue.extendleft((file, half, done.planned.params['model']) for half in reversed(halves))
            self.total += len(halves) - 1
        elif isinstance(error, client.Refused) and self.allow_other and done.planned.params['model'] == self.model:
            queue.appendleft((file, part, pricing.other_model(self.model)))
        elif isinstance(error, client.AccountError):
            self.fail(file, part, error.reason)
            self.halt = ('account', error.sentence)
        else:
            self.fail(file, part, error.reason)
        if self.halt is None and budget.over_run_cap(self.spent, self.override):
            self.halt = ('over_cap', f'This read reached its ${budget.run_cap():,.2f} cap; what it finished is kept.')

    def run(self, work):
        queue = deque((file, part, self.model) for file, part in work)
        self.total = len(queue)
        with calls.Runner(settings.AI_READ_PARALLEL) as runner:
            while queue or runner.busy:
                while queue and runner.has_room and self.halt is None:
                    file, part, model = queue.popleft()
                    planned = planned_call(self.reader, file, part, self.note(file), model=model, effort=self.effort)
                    try:
                        row = calls.reserve(planned, job=self.job)
                    except budget.OverLimit as exc:
                        self.halt = (HALTS.get(exc.kind, 'total_cap'), exc.sentence)
                        queue.appendleft((file, part, model))
                        break
                    runner.submit(planned, row)
                    self.progress.say(self._line(file, part), self._pct())
                if not runner.busy:
                    break
                for done, _row in runner.wait(self.progress.beat):
                    self.handle(done, queue)
                    self.progress.advance(self._pct())
        for file, part, _model in queue:  # what a halt left unread
            self.fail(file, part, self.halt[0] if self.halt else 'stopped')

    def _line(self, file, part):
        position = next((n for n, f in enumerate(self.files, start=1) if f is file), 1)
        if len(self.files) > 1:
            return f'File {position} of {len(self.files)}: reading {part.where()}'
        return f'Reading {part.where()}'

    def _pct(self):
        finished = len(self.parts) + len(self.failed)
        return 5 + 85 * finished / max(self.total, 1)


def _save_usage(job, run):
    Job.objects.filter(pk=job.pk).update(model=run.model, usage={**run.usage, 'calls': run.calls})


def _wait(job, land, sentence):
    Job.objects.filter(pk=job.pk).update(land=land, wait_reason=sentence[:200])


def build(job, run, extra):
    merged = run.reader.merge(run.parts, run.files)
    return run.reader.build_changes(job.deal, job.created_by, merged, run.files, extra)


def steps_up(changes, reading):
    """The Opus step-up (D76): a whole read with a hard finding, by a person who may use Opus 5.5 (D91)."""
    return (
        reading.model != pricing.OPUS
        and reading.allow_other
        and not (reading.failed or reading.halt)
        and any(finding.get('hard') for finding in changes.get('findings') or [])
    )


def step_up(job, progress, first, work, extra, changes):
    """(run, changes): Opus reads the same ranges again; its whole read replaces the first, which stays otherwise.
    The run's cost cap counts both reads."""
    progress.step(STEP_UP, 50)
    second = Run(job, progress, first.reader, first.files, model=pricing.OPUS, effort=first.effort)
    second.spent, second.usage, second.calls = first.spent, first.usage, first.calls
    second.run(work)
    _save_usage(job, second)
    if second.parts and not (second.failed or second.halt):
        return second, build(job, second, {**extra, 'model': pricing.OPUS, 'cost_usd': f'{second.spent:.4f}'})
    findings = [*(changes.get('findings') or []), {'text': STEP_UP_FAILED, 'hard': False}]
    return second, {**changes, 'cost_usd': f'{second.spent:.4f}', 'findings': findings}


def _local_only(job, reader, local, failed, model):
    """Every file was the owner's to read in code: its change set, without a Claude range (a census spreadsheet whose
    columns the offline mapper and the mapping assist mapped)."""
    spent = Job.objects.filter(pk=job.pk).values_list('cost_usd', flat=True).first() or 0
    extra = {'failed_parts': failed, 'left_out_pages': [], 'model': model, 'cost_usd': f'{spent:.4f}'}
    merged = reader.merge([], [])
    changes = reader.build_changes(job.deal, job.created_by, merged, [], {**extra, 'job': job.id, 'local': local})
    _wait(job, STAGED, 'Waiting for review.')
    return changes


def run(job, progress):
    """The `read` job's runner: returns the change set (Job.result); the land hook then lands it or leaves it
    waiting."""
    reader = registry.readers.get(job.target)
    if reader is None:
        raise JobFailed('Nothing reads files for this yet.')
    found = {doc.id: doc for doc in Document.all_objects.filter(deal_id=job.deal_id, pk__in=job.documents)}
    files, failed = read_files.from_documents([found[i] for i in job.documents if i in found])
    model, effort = model_for(job), settings.AI_EFFORT.get('read', 'high')
    local = None
    if reader.local is not None:  # files the owner reads in code (a census spreadsheet: the importer, D109)
        files, local = reader.local(job, progress, files)
    if local and not files:
        return _local_only(job, reader, local, failed, model)
    progress.step(f'Reading {len(files)} file{"s" if len(files) != 1 else ""} with Claude', 2)
    work, left_out = [], []
    only = (job.params or {}).get('pages') or None
    for file in files:
        parts, out, failure = read_files.plan(file, max_tokens=client.MAX_TOKENS, only_pages=only)
        if failure:
            failed.append(failure)
        work.extend((file, part) for part in parts)
        if out:
            left_out.append({'doc': file.id, 'pages': sorted(out), 'why': sorted(set(out.values()))})
    estimate = budget.run_estimate(model, [part for _file, part in work], prompt_tokens(reader))
    extra = {'failed_parts': failed, 'left_out_pages': left_out, 'estimate_usd': f'{estimate:.2f}', 'model': model}
    extra['job'] = job.id  # the read an owner's staged proposal points back to (CensusImport.job; slice 51)
    if local:
        extra['local'] = local
    if (job.params or {}).get('plan'):
        extra['attached'] = job.params['plan']  # "Attach SBC…": the plan the file is for (D38; slice 22)
    try:
        budget.check_run(job.deal_id, estimate, bool((job.params or {}).get('budget_override')))
    except budget.OverLimit as exc:
        _wait(job, OVER_BUDGET, exc.sentence)
        return {'v': 1, 'target': reader.target, 'documents': job.documents, 'over': exc.kind, **extra}
    if not work:
        raise JobFailed('Nothing in these files could be read.')
    reading = Run(job, progress, reader, files, model=model, effort=effort)
    try:
        reading.run(work)
        _save_usage(job, reading)
        if not reading.parts:
            raise JobFailed(reading.halt[1] if reading.halt else 'Claude could not read these files.')
        progress.step('Finding each value in its file', 92)
        extra.update(cost_usd=f'{reading.spent:.4f}', partial=bool(reading.failed or reading.halt))
        extra['failed_parts'] = failed + reading.failed
        if reading.halt:
            extra['halted'] = reading.halt[1]
        changes = build(job, reading, extra)
        if steps_up(changes, reading):
            reading, changes = step_up(job, progress, reading, work, extra, changes)
    except Stopped:  # Stop keeps what finished (D105): the change set waits, marked partial
        _save_usage(job, reading)
        extra.update(cost_usd=f'{reading.spent:.4f}', partial=True, failed_parts=failed + reading.failed)
        progress.result = build(job, reading, extra)
        _wait(job, STAGED, 'Stopped: what was read is waiting for review.')
        raise
    _wait(job, STAGED, reading.halt[1] if reading.halt else 'Waiting for review.')
    progress.step(changes.get('summary') or 'Read', 99)
    return changes
