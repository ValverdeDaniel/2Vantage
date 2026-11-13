from django.apps import AppConfig


class OverviewConfig(AppConfig):
    """The deal Overview (plan.md §7.16, §8.6; Part M). Last in the chain before golden: it may import every app to its
    left and nothing imports it. No models and no services (M.6, O.2): it reads each app's facts and assembles them,
    and every control on the tab writes through the app that owns the value. Slice 62 builds O2 (the shell, header,
    banners, tiles and the client box); Card 1, Card 2, the feed and the side cards follow in 63, data confidence in 64,
    the client page's read in 67."""

    name = 'overview'
