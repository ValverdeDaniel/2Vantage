from django.apps import AppConfig


class IntakeConfig(AppConfig):
    name = 'intake'

    def ready(self):
        from deals import activity

        from . import revert

        activity.reverters['intake'] = revert.revert  # Revert of a coverage edit, an intent gesture or a confirmation
