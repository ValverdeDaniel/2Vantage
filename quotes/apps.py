from django.apps import AppConfig


class QuotesConfig(AppConfig):
    name = 'quotes'

    def ready(self):
        from ai import registry as ai_registry
        from deals import activity, providers, stored_counts
        from intake import providers as intake_providers

        from . import facts, flags, locate_hooks, reader, revert, revert_enrollment, revert_read, turn
        from .selectors.intake_facts import quote_lines
        from .selectors.sales import client_has_sold
        from .services import enrollment, read_apply, saved_views

        activity.reverters['quotes'] = revert.revert  # O.1's seam: Revert in the Activity drawer and Undo
        activity.reverters[saved_views.AREA] = saved_views.revert  # an Update of a saved board setup (F28)
        activity.reverters[enrollment.AREA] = revert_enrollment.revert  # a typed-enrollment save (F85, F88, F91)
        activity.reverters[read_apply.AREA] = revert_read.revert  # a used quote read: ↶ Undo this run (D73)
        providers.fill('client_has_sold', client_has_sold)  # Back to prospect's refusal (§5.1)
        intake_providers.fill('quote_lines', quote_lines)  # line states, lines off the proposal, from_plans (B24)
        intake_providers.fill('headcount', facts.headcount)  # the one headcount: tier, band, printed counts (§5.7)
        # "Check this file" (E59): which plan values came from a file, and where the locator's answers go.
        ai_registry.register_locate('quotes', locate_hooks.queries, locate_hooks.save)
        reader.register()  # Claude's quote reader (slice 18): prompt, schema, merge and change set
        turn.register()  # Work with Claude's chat (slice 24): set_board, propose_changes, clear_line, the table
        stored_counts.register('plan flags', flags.rebuild)  # Plan.flags against a rebuild (O.3.7, Q.3 #9)
