"""quotes' half of Work with Claude's chat (plan.md §10.6; O.3.3's registry; slice 24).

`register()`, from `QuotesConfig.ready()`, fills ai's seams: the tools `set_board` (`board.py`), `propose_changes`
and `clear_line` (`edits.py`), `merge_plans` (`merge.py`) and `check_values` (`check.py`; slice 22); the context
provider that tells a turn the plan table and the board (`table.py`); the carriers on the deal's plans (whose admin
notes a turn carries, D119); and the turn owner that lands a turn's plan changes (`apply.py`). ai imports none of
this: it calls what is registered.
"""


def _plan_carriers(deal):
    from ..models import Plan

    return Plan.objects.filter(deal=deal).values_list('carrier', flat=True).distinct()


def register():
    from ai import registry

    from . import apply, board, check, edits, merge, table

    for tool in (board.TOOL, edits.PROPOSE, edits.CLEAR, merge.MERGE, check.CHECK):
        registry.register_tool(tool)
    registry.register_context('plans', table.provide, order=20)
    registry.register_turn_owner('quotes', apply.apply, order=20)
    if _plan_carriers not in registry.deal_carriers:
        registry.deal_carriers.append(_plan_carriers)
