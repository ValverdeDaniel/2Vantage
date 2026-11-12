"""Claude's `rank_plans` (plan.md §10.6; D6, D81, D96, F111, OQ44; slice 37): asked in the chat, Claude starts ⚖ Rank
plans on one line — the same `rank` job the drawer's button starts (`rank.start.start_rank`), in the work lane, so
the turn never waits for it. The job stars the 5–8 quoted plans that best fit the client guidance, each with its
reason, through the star rule and within `room()`, and shows on the strip with ↶ Undo this run. With `plan_ids` it
ranks among those plans only, and a star outside them stays (OQ44). Refused in the door's words: no guidance ("Add
client guidance first"), the table locked, no quoted plans. A job is the AI's own record, not deal data, so starting
one is no write to the table.
"""

from rest_framework.exceptions import ValidationError

from ai import tools
from ai.registry import Tool
from deals import lines
from deals.activity import Refused

from ..rank.start import start_rank

STARTED = (
    'Started ranking the {line} plans against the client guidance{among}, in a job of its own. When it finishes it '
    'stars the plans that fit best, each with its reason, replacing the stars {where}; the producer can undo it on '
    'the strip.'
)


def rank_plans(turn, data):
    line = tools.text(data.get('line'), 'line', 30)
    if line not in lines.BY_KEY:
        raise tools.ToolRefused(f'"{line}" is not a line of coverage.')
    ids = list(dict.fromkeys(tools.integers(data.get('plan_ids') or [], 'plan_ids')))
    try:
        start_rank(turn.user, turn.deal, line, plan_ids=ids or None)
    except Refused as exc:
        raise tools.ToolRefused(exc.sentence) from None
    except ValidationError:
        raise tools.ToolRefused(f'Those plans are not quoted plans of {lines.label(line)} on this deal.') from None
    among = f' among the {len(ids)} plans named' if ids else ''
    where = 'among those plans (stars on other plans stay)' if ids else 'on that line'
    return STARTED.format(line=lines.label(line), among=among, where=where)


RANK = Tool(
    name='rank_plans',
    owner='quotes',
    order=62,
    description=(
        'Rank one line’s quoted plans against the client guidance, in a job of its own: it stars the 5–8 that fit '
        'best, each with a reason, replacing that line’s stars (only those among plan_ids when given). Needs client '
        'guidance. Use it when the producer asks to rank, shortlist or star the plans that fit.'
    ),
    schema=tools.schema(
        {
            'line': {'type': 'string', 'enum': list(lines.LINE_KEYS)},
            'plan_ids': {
                'type': 'array',
                'items': {'type': 'integer'},
                'description': 'Plan ids from <plans> to rank among; empty for every quoted plan of the line.',
            },
        }
    ),
    run=rank_plans,
)
