from django.apps import AppConfig


class QuotesConfig(AppConfig):
    name = 'quotes'

    def ready(self):
        from ai import registry as ai_registry
        from deals import activity, providers

        from . import locate_hooks, revert
        from .selectors.sales import client_has_sold

        activity.reverters['quotes'] = revert.revert  # O.1's seam: Revert in the Activity drawer and Undo
        providers.fill('client_has_sold', client_has_sold)  # Back to prospect's refusal (§5.1)
        # "Check this file" (E59): which plan values came from a file, and where the locator's answers go.
        ai_registry.register_locate('quotes', locate_hooks.queries, locate_hooks.save)
