from django.apps import AppConfig


class RfpConfig(AppConfig):
    """The RFP tab (plan.md §6.10, §7.11; Part K). Slice 26 holds only `RfpRequest` and `asked_by_line()`, so the
    proposal's Markets checked can read who was asked (J63, K117); slices 44–46 bring the tab, services and files."""

    name = 'rfp'
