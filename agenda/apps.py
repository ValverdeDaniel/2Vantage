from django.apps import AppConfig


class AgendaConfig(AppConfig):
    """Agenda (plan.md §5.9, §6.13, §7.15, §8.7; Part I). Slice 60 builds AG1: the step engine over every app's facts
    (`steps/`, `marks`, `rows`), people's marks (Later, Done anyway), tasks added by hand, and the deal's Agenda tab.
    The shell's journey, the Work queue and the home figures follow in slice 61, the client Agenda in 68. Agenda never
    writes a module value or a stage (O.2): its only rows are `StepMark` and `Task`."""

    name = 'agenda'

    def ready(self):
        from deals import activity

        from . import revert
        from .services import common

        activity.reverters[common.AREA] = revert.revert  # Later, Done anyway, and a task's date, tick, person, delete
