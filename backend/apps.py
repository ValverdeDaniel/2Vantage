from django.apps import AppConfig


class BackendConfig(AppConfig):
    name = 'backend'
    label = 'backend'

    def ready(self):
        from . import checks  # noqa: F401 — registers the deploy checks
