from django.apps import AppConfig


class AiConfig(AppConfig):
    name = 'ai'
    verbose_name = 'AI and jobs'

    def ready(self):
        from . import check

        check.register()  # the `locate` job kind (E59); owners register their locate hooks in their own ready()
