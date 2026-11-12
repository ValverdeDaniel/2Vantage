from django.apps import AppConfig


class QuestionnaireConfig(AppConfig):
    name = 'questionnaire'

    def ready(self):
        from deals import activity, stored_counts
        from intake import providers
        from quotes import providers as quote_providers

        from . import checks, flags, revert  # noqa: F401 (checks registers the start-up checks)
        from .selectors.disclosure import disclosure_state
        from .selectors.items import questionnaire_items

        providers.fill('questionnaire_items', questionnaire_items)  # the checklist's form rows (B22, B26; G11)
        quote_providers.fill('disclosure_state', disclosure_state)  # the stop-loss Binding Notes (G117, O.6 #47)
        activity.reverters['questionnaire'] = revert.revert  # answers, rows and marks (G123, E88)
        stored_counts.register('questionnaire flags', flags.rebuild)  # Questionnaire.flags (O.3.7, Q.3 #9)
