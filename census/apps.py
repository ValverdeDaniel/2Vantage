from django.apps import AppConfig


class CensusConfig(AppConfig):
    name = 'census'

    def ready(self):
        from deals import activity
        from intake import providers as intake_providers
        from intake import signals as intake_signals

        from . import facts, revert

        activity.reverters['census'] = revert.revert  # key-only rows: refused with a sentence
        intake_providers.fill('census_state', facts.state)  # "Census OK" for intake (B33, C23)
        # The lines to quote or medical's in-force answer moved: what is required moved with them (§5.3.3).
        intake_signals.coverage_changed.connect(_refresh, dispatch_uid='census.refresh_facts')


def _refresh(sender, deal_id, **kwargs):
    from . import facts

    facts.refresh(deal_id)
