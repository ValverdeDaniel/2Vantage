from django.apps import AppConfig


class QuotesConfig(AppConfig):
    name = 'quotes'

    def ready(self):
        from deals import activity, providers

        from . import revert
        from .selectors.sales import client_has_sold

        activity.reverters['quotes'] = revert.revert  # O.1's seam: Revert in the Activity drawer and Undo
        providers.fill('client_has_sold', client_has_sold)  # Back to prospect's refusal (§5.1)
