from django.apps import AppConfig


class AiConfig(AppConfig):
    name = 'ai'
    verbose_name = 'AI and jobs'

    def ready(self):
        from deals.activity import reverters

        from . import check, kinds, reading, recheck, registry, turn, turn_files
        from .services import deal_ai, landing, turns

        check.register()  # the `locate` job kind (E59); owners register their locate hooks in their own ready()
        # Every reader runs through ai/reading.py (slice 18); a finished read lands by itself or waits (D71, slice 20).
        registry.register_kind(kinds.READ, reading.run, land=landing.on_finish)
        # ✦ Ask Claude to re-check (slice 22): flagged values read again; a person applies what it proposes (D93).
        registry.register_kind(kinds.RECHECK, recheck.run, land=landing.on_recheck)
        # A chat turn (slice 24): its changes land by themselves for direct people, or wait (services/turns.py).
        registry.register_kind(kinds.TURN, turn.run, land=turns.on_finish)
        registry.register_tool(turn_files.READ_DOCUMENT)
        reverters[deal_ai.AREA] = deal_ai.revert  # the table lock and the budget (D100, D104)
