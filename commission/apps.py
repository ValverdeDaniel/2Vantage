from django.apps import AppConfig


class CommissionConfig(AppConfig):
    """Commission (plan.md §5.6, §6.9, §7.10; Part H). Slice 48: the agreed rates and expected revenue, the split
    editor (deal and client scope), Producers & partners and Settings. Slice 49 books at the sale (`sold_changed`),
    the Book, By person and the CAA disclosure. The ledger waits (OQ6 is No)."""

    name = 'commission'

    def ready(self):
        from deals import activity
        from quotes import signals

        from . import revert, services

        activity.reverters[services.AREA] = revert.revert  # rates, the year, splits, parties, defaults, records (H113)
        # The seam from quotes (O.1): quotes sends `sold_changed` once a sale commits; commission books (H25).
        signals.sold_changed.connect(services.on_sold_changed, dispatch_uid='commission.book_at_sale')
