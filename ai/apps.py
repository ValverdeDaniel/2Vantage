from django.apps import AppConfig


class AiConfig(AppConfig):
    name = 'ai'
    verbose_name = 'AI and jobs'

    def ready(self):
        from . import check, kinds, reading, registry
        from .services import landing

        check.register()  # the `locate` job kind (E59); owners register their locate hooks in their own ready()
        # Every reader runs through ai/reading.py (slice 18); a finished read lands by itself or waits (D71, slice 20).
        registry.register_kind(kinds.READ, reading.run, land=landing.on_finish)
