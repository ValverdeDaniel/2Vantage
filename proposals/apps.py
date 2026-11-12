from django.apps import AppConfig


class ProposalsConfig(AppConfig):
    name = 'proposals'

    def ready(self):
        from ai import kinds as job_kinds
        from ai import registry
        from deals import activity
        from intake import signals as intake_signals
        from quotes import signals

        from . import firm_services, revert, services, template_services
        from .issues import build as issue_build
        from .viewer import turn as viewer_turn

        activity.reverters[services.AREA] = revert.revert  # a setting or a card's mark (J.6.4)
        # The firm's pages and team, and saved templates: firm rows (slice 34; J68, J155).
        activity.reverters[firm_services.AREA] = firm_services.revert
        activity.reverters[template_services.AREA] = template_services.revert
        # Work with Claude is told what the Export viewer shows, as the browser sent it (J120; slice 30).
        registry.register_context('export_viewer', viewer_turn.provide, order=30)
        # A star, slot, order or Claude write takes the line's Plans card mark off (J19).
        signals.plans_changed.connect(services.on_plans_changed, dispatch_uid='proposals.plans_changed')
        # An intent or coverage edit takes the Coverage & marketing intent card's mark off (J46).
        intake_signals.coverage_changed.connect(services.on_coverage_changed, dispatch_uid='proposals.coverage')
        # Issue to client (J103; slice 32): the files built by the worker, outside every lock, then stored.
        registry.register_kind(job_kinds.ISSUE, issue_build.run)
