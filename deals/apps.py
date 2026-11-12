from django.apps import AppConfig


class DealsConfig(AppConfig):
    name = 'deals'

    def ready(self):
        from . import activity
        from .services import archive, facts, notes, status

        activity.reverters[status.AREA] = status.revert  # Revert of a hand status move (§5.1, O.1)
        activity.reverters[facts.AREA] = facts.revert  # an owner, the deal size or the agent of record (M27, M29)
        activity.reverters[archive.AREA] = archive.revert  # Archive or Restore back (M9)
        activity.reverters[notes.AREA] = notes.revert  # the Undo of a note's delete, pin or kind (M77)
