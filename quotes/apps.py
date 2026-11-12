from django.apps import AppConfig


class QuotesConfig(AppConfig):
    name = 'quotes'

    def ready(self):
        from ai import registry as ai_registry
        from deals import activity, providers
        from intake import providers as intake_providers

        from . import locate_hooks, revert
        from .selectors.intake_facts import quote_lines
        from .selectors.sales import client_has_sold
        from .services import saved_views

        activity.reverters['quotes'] = revert.revert  # O.1's seam: Revert in the Activity drawer and Undo
        activity.reverters[saved_views.AREA] = saved_views.revert  # an Update of a saved board setup (F28)
        providers.fill('client_has_sold', client_has_sold)  # Back to prospect's refusal (§5.1)
        intake_providers.fill('quote_lines', quote_lines)  # line states, lines off the proposal, from_plans (B24)
        # "Check this file" (E59): which plan values came from a file, and where the locator's answers go.
        ai_registry.register_locate('quotes', locate_hooks.queries, locate_hooks.save)
