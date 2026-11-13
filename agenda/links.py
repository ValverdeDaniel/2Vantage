"""Where each row opens (I13; I.6 `link_for`): one rule over the catalogue's tab map, never a path built by hand.

`link_for(deal_id, tab, params)` → '/deals/31/census?import=4'. The deal page's tabs are plan.md §8.1's; an unbuilt tab
opens the deal's default tab (A26), so an older step never leads nowhere.
"""

from urllib.parse import urlencode


def link_for(deal_id, tab, params=None):
    if not tab:
        return None
    query = urlencode({key: value for key, value in (params or {}).items() if value not in (None, '')})
    return f'/deals/{deal_id}/{tab}' + (f'?{query}' if query else '')


def focus(deal_id, row_id):
    """A row on the deal's own Agenda, scrolled to and flashed (I7): `?focus=task:12`."""
    return link_for(deal_id, 'agenda', {'focus': row_id})


def nudge(deal_id, link_id):
    """A reminder to nudge someone opens that link's settings card, where the reminder is set (I35; old 891f1b3
    `tasks/payload.task_link`), on their link as the card's Edit opens a live one (the reminder is set there, slice
    57): `/deals/31/review?view=request&target=link%3A12&settings=12`."""
    return link_for(deal_id, 'review', {'view': 'request', 'target': f'link:{link_id}', 'settings': link_id})
