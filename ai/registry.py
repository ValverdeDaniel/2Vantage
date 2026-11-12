"""What other apps register into ai, from their AppConfig.ready() (plan.md §10.2; O.1's seam, O.3.3).

ai sits left of every value owner in the chain, so it never imports them: they fill these tables.

- `job_kinds` {kind: JobKind(lane, run, land)}: how a job of that kind runs. `run(job, progress)` does the work and
  returns the job's `result`; `progress` (ai.progress.Progress) reports steps and stops it between steps. `land(job,
  result) -> {job fields}`, when given, runs in the transaction that ends the job (`running._finish`), so a read that
  lands by itself (D71, slice 20) and the job's end commit together, or not at all. ai registers `locate` and `read`
  itself; quotes adds `rank` and proposals `issue` in their slices.
- `locate_hooks` {owner: LocateHook(queries, save)}: the value owners whose values the locator checks (E.6, O.3.1).
  `queries(deal, document, recheck)` -> [(ref, Query or Located)] for the owner's values that name `document`
  (`recheck` False: only values never checked, or checked by an older locator); `save(user, deal, document,
  [(ref, loc)])` stores each answer as the value's `loc` through deals.values.set_loc, in one transaction, and
  returns {'saved': n, 'areas': [frontend areas to refetch]}. A `ref` is the owner's own and opaque to ai.
- `readers` {target: Reader}: each value owner's reader (slice 18: quotes). `ai/reading.py` cuts the files into
  ranges, sends each with the reader's `prompt` and `schema`, and hands the answers to the reader, which merges them
  (`merge`), finds each value in its file and builds the change set (`build_changes`); `apply` and `undo` land it
  through the owner's services and take it back (slice 19). `corpus` and `score` feed the Eval lane
  (`manage.py reader_eval`).
- `context`, `tools`: the chat's context providers and tools (slice 24; empty until then).
"""

from collections import namedtuple
from dataclasses import dataclass, field

from . import kinds

JobKind = namedtuple('JobKind', 'lane run land', defaults=(None,))
LocateHook = namedtuple('LocateHook', 'queries save')

job_kinds = {}
locate_hooks = {}
readers = {}
context = {}
tools = {}


def register_kind(kind, run, land=None):
    """`run(job, progress) -> result` for every job of `kind`, in the kind's lane (kinds.LANE_OF); `land(job, result)`
    as above."""
    if kind not in kinds.LANE_OF:
        raise ValueError(f'Unknown job kind: {kind}')
    job_kinds[kind] = JobKind(kinds.LANE_OF[kind], run, land)


def register_locate(owner, queries, save):
    locate_hooks[owner] = LocateHook(queries, save)


@dataclass(frozen=True)
class Reader:
    """One target's reader (O.3.3). `prompt` and `schema` are the same bytes for every deal, so they cache.
    - `note(file, context) -> str`: the per-call note, outside the cache (what the file was filed as; never a name).
    - `merge(parts, files) -> merged`: the answers of every range of every file, joined (parts: [(file, range, data)]).
    - `build_changes(deal, user, merged, files, extra) -> change set` (D.6's shape); `extra` holds the failed parts,
      left-out pages and the run's cost.
    - `must_review`: its reads always wait for a person (SBC, intake, census, questionnaire).
    - `apply(user, deal, job, select=None, picks=None) -> landed`: lands the chosen parts of `job.result` through the
      owner's services in one transaction, returning what it wrote ({activity_id, activity_ids, plan_ids, areas,
      summary, skipped, …}); `undo(user, deal, job, force=False) -> {reverted, kept, skipped, at, by}` reverts that
      landing, raising `deals.activity.Refused` when something changed since (slice 19). `discard`: slice 51's census.
    - `corpus()` and `score(key, merged)`: the Eval lane's cases and scorer."""

    target: str
    kinds: tuple
    prompt: str
    schema: dict
    version: int
    note: object
    merge: object
    build_changes: object
    must_review: bool = False
    apply: object = None
    undo: object = None
    discard: object = None
    can_access: object = None
    on_client_upload: bool = False
    corpus: object = None
    score: object = None
    labels: dict = field(default_factory=dict)  # {document kind: label} for refusals in words


def register_reader(reader):
    if reader.target not in kinds.TARGETS:
        raise ValueError(f'Unknown reader target: {reader.target}')
    readers[reader.target] = reader
