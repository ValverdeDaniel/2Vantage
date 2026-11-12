from django.apps import AppConfig


class RfpConfig(AppConfig):
    """The RFP tab (plan.md §6.10, §7.11; Part K). Slice 26 made `RfpRequest` and `asked_by_line()` (Markets checked,
    J63, K117); slice 44 the page, the request's settings and the cards' marks; slices 45–46 bring the files and sends.
    """

    name = 'rfp'

    def ready(self):
        from deals import activity
        from intake import signals as intake_signals

        from . import revert, services

        activity.reverters[services.AREA] = revert.revert  # a burst of settings edits, or a card's mark (K115)
        # An intent or coverage edit takes the coverage card's mark off (K10), after census refreshes its counts.
        intake_signals.coverage_changed.connect(services.clear_coverage_mark, dispatch_uid='rfp.coverage')
