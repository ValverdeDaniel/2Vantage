"""What other apps register into ai, from their AppConfig.ready() (plan.md §10.2; O.1's seam, O.3.3).

ai sits left of every value owner in the chain, so it never imports them: they fill these tables.

- `job_kinds` {kind: JobKind(lane, run)}: how a job of that kind runs. `run(job, progress)` does the work and returns
  the job's `result`; `progress` (ai.progress.Progress) reports steps and stops it between steps. ai registers
  `locate` itself (ai/check.py); quotes adds `rank` and proposals `issue` in their slices.
- `locate_hooks` {owner: LocateHook(queries, save)}: the value owners whose values the locator checks (E.6, O.3.1).
  `queries(deal, document, recheck)` -> [(ref, Query or Located)] for the owner's values that name `document`
  (`recheck` False: only values never checked, or checked by an older locator); `save(user, deal, document,
  [(ref, loc)])` stores each answer as the value's `loc` through deals.values.set_loc, in one transaction, and
  returns {'saved': n, 'areas': [frontend areas to refetch]}. A `ref` is the owner's own and opaque to ai.
- `readers`, `context`, `tools`: the readers, context providers and chat tools of slices 18–24 (empty until then).
"""

from collections import namedtuple

from . import kinds

JobKind = namedtuple('JobKind', 'lane run')
LocateHook = namedtuple('LocateHook', 'queries save')

job_kinds = {}
locate_hooks = {}
readers = {}
context = {}
tools = {}


def register_kind(kind, run):
    """`run(job, progress) -> result` for every job of `kind`, in the kind's lane (kinds.LANE_OF)."""
    if kind not in kinds.LANE_OF:
        raise ValueError(f'Unknown job kind: {kind}')
    job_kinds[kind] = JobKind(kinds.LANE_OF[kind], run)


def register_locate(owner, queries, save):
    locate_hooks[owner] = LocateHook(queries, save)
