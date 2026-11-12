from django.apps import AppConfig


class ReviewConfig(AppConfig):
    """Review & requests (plan.md §5.8, §6.12, §7.13; Part L). Slice 53 builds V1: the models, the rules, the link
    services, a minimal New link, the Waiting lane, `summary.facts` and the tab's own counts. The portal (54), queues
    and approvals (55), the tray (56), the builder (57), questionnaires (58) and client reads (59) follow."""

    name = 'review'

    def ready(self):
        from deals import activity
        from rfp.check import providers

        from . import export_check, revert
        from .services import common

        activity.reverters[common.AREA] = revert.revert  # sent, unsent, extended, turned off and on, closed
        # The client's census answers in every file's check (L120; slice 55): rfp never imports review (O.3.4).
        providers.register('review', export_check.problems, export_check.stamp)
