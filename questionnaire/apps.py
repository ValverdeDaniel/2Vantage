from django.apps import AppConfig


class QuestionnaireConfig(AppConfig):
    name = 'questionnaire'

    def ready(self):
        from deals import activity, stored_counts
        from intake import providers

        from . import checks, flags, revert  # noqa: F401 (checks registers the start-up checks)
        from .selectors.items import questionnaire_items

        providers.fill('questionnaire_items', questionnaire_items)  # the checklist's form rows (B22, B26; G11)
        activity.reverters['questionnaire'] = revert.revert  # answers, rows and marks (G123, E88)
        stored_counts.register('questionnaire flags', flags.rebuild)  # Questionnaire.flags (O.3.7, Q.3 #9)
