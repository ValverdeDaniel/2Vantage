from django.apps import AppConfig


class DealsConfig(AppConfig):
    name = 'deals'

    def ready(self):
        from . import activity
        from .services import status

        activity.reverters[status.AREA] = status.revert  # Revert of a hand status move (§5.1, O.1)
