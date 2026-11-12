from django.apps import AppConfig


class CommissionConfig(AppConfig):
    """Commission (plan.md §5.6, §6.9, §7.10; Part H). Slice 48: the agreed rates and expected revenue, the split
    editor (deal and client scope), Producers & partners and Settings. Slice 49 books at the sale (`sold_changed`),
    the Book and By person. The ledger waits (OQ6 is No)."""

    name = 'commission'

    def ready(self):
        from deals import activity

        from . import revert, services

        activity.reverters[services.AREA] = revert.revert  # rates, the year, splits, parties and the defaults (H113)
