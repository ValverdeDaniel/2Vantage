"""The ai app's vocabularies (plan.md §6.4, §10.2; O.3.3, D.6). Python constants, as every vocabulary is (rule 1).

Kinds of job, the lane each runs in, and a job's statuses. Lanes keep long work from blocking short work: a locate or
an Issue never waits behind a long read, because the worker runs one job per deal and lane at a time.
"""

WORK, CHAT, SYSTEM = 'work', 'chat', 'system'
LANES = (WORK, CHAT, SYSTEM)

READ, TURN, RECHECK, RANK, LOCATE, ISSUE = 'read', 'turn', 'recheck', 'rank', 'locate', 'issue'
LANE_OF = {READ: WORK, RECHECK: WORK, RANK: WORK, TURN: CHAT, LOCATE: SYSTEM, ISSUE: SYSTEM}
KINDS = tuple(LANE_OF)

# The readers a `read` or `recheck` names in `target` (slice 18 on); a locate or an issue has none.
TARGETS = ('quotes', 'sbc', 'intake', 'census', 'questionnaire', 'commission_statement')

QUEUED, RUNNING, DONE, FAILED, CANCELLED = 'queued', 'running', 'done', 'failed', 'cancelled'
STATUSES = (QUEUED, RUNNING, DONE, FAILED, CANCELLED)
ACTIVE = (QUEUED, RUNNING)
FINISHED = (DONE, FAILED, CANCELLED)

# How a finished job ended, beyond its status.
STOPPED, REAPED = 'stopped', 'reaped'

STEPS_KEPT = 50  # `steps` holds at most this many short lines, never file text or names (§6.4)
STEP_LENGTH = 120
