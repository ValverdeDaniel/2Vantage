from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    name = 'documents'

    def ready(self):
        from deals import activity

        from . import revert

        activity.reverters['documents'] = revert.revert  # Revert of a file's details or its removal (O.1, E74)
