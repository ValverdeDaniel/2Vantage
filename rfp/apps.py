from django.apps import AppConfig


class RfpConfig(AppConfig):
    """The RFP tab (plan.md §6.10, §7.11; Part K). Slice 26 made `RfpRequest` and `asked_by_line()` (Markets checked,
    J63, K117); slice 44 the page, the request's settings and the cards' marks; slice 45 the carrier census files, the
    packet's census rows, the lens and census's `carrier_required`; slice 46 the forms, packet, drafts and sends.
    """

    name = 'rfp'

    def ready(self):
        from census import providers as census_providers
        from deals import activity
        from intake import signals as intake_signals

        from . import revert, services
        from .formats import required

        activity.reverters[services.AREA] = revert.revert  # a burst of settings edits, or a card's mark (K115)
        # The census cells the files the request sends require, flagged on the Census tab (K124, §5.3.3 step 6).
        census_providers.fill('carrier_required', required.carrier_required)
        # An intent or coverage edit takes the coverage card's mark off (K10), after census refreshes its counts.
        intake_signals.coverage_changed.connect(services.clear_coverage_mark, dispatch_uid='rfp.coverage')
