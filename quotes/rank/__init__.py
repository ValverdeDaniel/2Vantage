"""⚖ Rank plans (plan.md §5.4, §7.5, §10.4; D6, D36, D96, D97, F111, OQ44; slice 37): Claude stars the 5–8 quoted
plans of one line that best fit the client guidance, each with its reason, through the star rule and within `room()`.

- `rules.py` (pure): what Rank replaces and may star, Claude's picks within the room, curated lines;
- `plans.py` and `guidance.py`: what Claude is told; `prompt.py`: the system prompt and the answer's schema;
- `start.py`: the door (`deals/{id}/ai/rank/`, `rank_views.py`), Claude's `rank_plans` (`turn/rank.py`) and the rank
  after a read; `job.py`: the `rank` job kind, run by the worker, whose landing writes through
  `services.rank.rank` with ↶ Undo this run.
`register()`, from QuotesConfig.ready(), gives ai the `rank` kind (O.1's seam: ai never imports quotes).
"""


def register():
    from ai import kinds, registry

    from . import job

    registry.register_kind(kinds.RANK, job.run, land=job.land)
