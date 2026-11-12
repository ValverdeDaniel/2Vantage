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
- `context` {name: ContextProvider(order, fn)}: what a chat turn is told about the deal, never stored (D78; slice 24).
  `fn(deal, page) -> text` ('' for nothing), where `page` is what the person's tab shows ({tab, board, viewer}); the
  turn joins them in `order`. quotes tells the plan table and the board, intake the client guidance.
- `tools` {name: Tool}: Claude's strict chat tools (D81, O.3.3; slice 24), sent in `order` (a fixed list: the cache
  key). `run(turn, data) -> str` validates `data` in code and answers in words for Claude; it raises
  `ai.tools.ToolRefused(sentence)` for input it will not take. A tool never writes: it adds items to the turn's change
  set (`turn.add(item)`) or sets the board (`turn.board`), and the change set lands through its owner (below).
- `turn_owners` {owner: TurnOwner(order, apply)}: who lands a turn's items (`item['owner']`), in the chain's lock
  order. `apply(user, deal, job, items) -> {activity_ids, plan_ids, areas, summary, skipped}` writes them through the
  owner's services in the caller's transaction; ↶ Undo this run reverts those Activity rows.
- `checkers` {owner: Checker}: the value owners whose flagged values Claude re-checks (D40, D93, E77; slice 22). The
  `recheck` job (`ai/recheck.py`) asks the owner for its claims, has Claude read each against its page, and hands
  the verdicts back to the owner, whose change set a person applies (D-119: never by itself).
"""

from collections import namedtuple
from dataclasses import dataclass, field

from . import kinds

JobKind = namedtuple('JobKind', 'lane run land', defaults=(None,))
LocateHook = namedtuple('LocateHook', 'queries save')
ContextProvider = namedtuple('ContextProvider', 'order fn')
TurnOwner = namedtuple('TurnOwner', 'order apply')

job_kinds = {}
locate_hooks = {}
readers = {}
context = {}
tools = {}
turn_owners = {}
deal_carriers = []  # fn(deal) -> carrier names on the deal's plans (quotes): whose carrier notes a turn carries


@dataclass(frozen=True)
class Tool:
    """One chat tool (D81): `schema` is its strict input schema (every object closes with additionalProperties
    false); `owner` is the app that registered it."""

    name: str
    owner: str
    order: int
    description: str
    schema: dict
    run: object


def register_tool(tool):
    tools[tool.name] = tool


def register_context(name, fn, order):
    context[name] = ContextProvider(order, fn)


def register_turn_owner(owner, apply, order):
    turn_owners[owner] = TurnOwner(order, apply)


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


@dataclass(frozen=True)
class Checker:
    """One owner's re-check (D93's one check mode: agree, fix or not found; slice 22).
    - `claims(deal, scope) -> [claim]`: the values to re-check, each `{ref, doc, page, cell, label, value}` (`ref` is
      the owner's and opaque here; `label` names the plan and the field, never a person). `scope` is `{refs?,
      plan_ids?, document_ids?}`; none of them: every open warning on the deal. Raises ValidationError for ids that
      are not the deal's.
    - `build_changes(deal, claims, verdicts, extra) -> change set`: D.6's shape; items the person applies (`confirm`
      for a value Claude agrees with, `set_values` for a fix), `unverified` for the values not found on their page.
    - `apply(user, deal, job, select=None, picks=None) -> landed` and `undo(user, deal, job, force=False)`: as a
      Reader's: a person applies the change set through the owner's services, and ↶ Undo this run takes it back."""

    owner: str
    claims: object
    build_changes: object
    apply: object
    undo: object


checkers = {}
flag_counts = []  # fn(deal) -> the open warnings on the deal's values (quotes): the strip's "✦ Re-check N flags" (E80)


def register_checker(checker):
    if checker.owner not in kinds.TARGETS:
        raise ValueError(f'Unknown checker owner: {checker.owner}')
    checkers[checker.owner] = checker
