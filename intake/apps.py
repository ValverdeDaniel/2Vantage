from django.apps import AppConfig


class IntakeConfig(AppConfig):
    name = 'intake'

    def ready(self):
        from deals import activity, stored_counts

        from . import flags, reader, revert, turn

        activity.reverters['intake'] = revert.revert  # Revert: answers, coverage, intent, confirmations
        stored_counts.register('intake flags', flags.rebuild)  # Intake.flags against a rebuild (O.3.7, Q.3 #9)
        turn.register()  # Work with Claude's chat (slice 24): update_client_guidance and the guidance context
        reader.register()  # Claude's intake reader (slice 51, B40): only behind the PHI-gate switch
