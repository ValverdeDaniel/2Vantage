from django.apps import AppConfig


class ProposalsConfig(AppConfig):
    name = 'proposals'

    def ready(self):
        from ai import registry
        from deals import activity
        from intake import signals as intake_signals
        from quotes import signals

        from . import revert, services
        from .viewer import turn as viewer_turn

        activity.reverters[services.AREA] = revert.revert  # a setting or a card's mark (J.6.4)
        # Work with Claude is told what the Export viewer shows, as the browser sent it (J120; slice 30).
        registry.register_context('export_viewer', viewer_turn.provide, order=30)
        # A star, slot, order or Claude write takes the line's Plans card mark off (J19).
        signals.plans_changed.connect(services.on_plans_changed, dispatch_uid='proposals.plans_changed')
        # An intent or coverage edit takes the Coverage & marketing intent card's mark off (J46).
        intake_signals.coverage_changed.connect(services.on_coverage_changed, dispatch_uid='proposals.coverage')
