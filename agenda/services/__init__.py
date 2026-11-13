"""Agenda's writes (rule 3; I.6 services): marks (`marks.py`) and tasks (`tasks.py`). Nothing else in agenda writes,
and agenda never writes a module value or a stage (O.2)."""

from .marks import clear_mark, log_follow_up, set_done_anyway, set_later
from .tasks import add_task, delete_task, move_task, update_task

__all__ = [
    'add_task',
    'clear_mark',
    'delete_task',
    'log_follow_up',
    'move_task',
    'set_done_anyway',
    'set_later',
    'update_task',
]
