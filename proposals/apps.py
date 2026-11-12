from django.apps import AppConfig


class ProposalsConfig(AppConfig):
    name = 'proposals'

    def ready(self):
        from deals import activity
        from quotes import signals

        from . import revert, services

        activity.reverters[services.AREA] = revert.revert  # a setting or a card's mark (J.6.4)
        # A star, slot, order or Claude write takes the line's Plans card mark off (J19).
        signals.plans_changed.connect(services.on_plans_changed, dispatch_uid='proposals.plans_changed')
