"""Claude's `check_values` (plan.md §10.6; D81, D93; slice 22; the old start_flag_check `via_chat`): asked in the chat,
Claude starts ✦ Ask Claude to re-check over the flagged values on some plans, one file, or the whole table. The
re-check is its own job on the work lane (`ai.services.start_recheck`): it reads those values again against their
pages and waits on its card for the producer to apply it, whoever asked (D-119). A job is the AI's own record, not
deal data, so starting one is no write to the table.
"""

from rest_framework.exceptions import ValidationError

from ai import tools
from ai.registry import Tool
from deals.activity import Refused

STARTED = (
    'Started a re-check of {n} flagged value{s}. Its card shows in Work with Claude when it is done: nothing changes '
    'until the producer applies what it proposes.'
)


def check_values(turn, data):
    from ai.services import start_recheck

    plan_ids = tools.integers(data.get('plan_ids') or [], 'plan_ids')
    document_id = tools.integer(data.get('document_id') or 0, 'document_id')
    try:
        job, _created = start_recheck(
            turn.user,
            turn.deal,
            plan_ids=plan_ids or None,
            document_ids=[document_id] if document_id else None,
        )
    except Refused as exc:
        raise tools.ToolRefused(exc.sentence) from None
    except ValidationError as exc:
        raise tools.ToolRefused('Those plans or that file are not on this deal.') from exc
    count = len((job.params or {}).get('refs') or [])
    return STARTED.format(n=count, s='' if count == 1 else 's')


CHECK = Tool(
    name='check_values',
    owner='quotes',
    order=48,
    description=(
        'Re-check the flagged values (those to review) against their pages: on some plans, in one file, or on the '
        'whole table when both are empty. Claude reads them again in its own job; the producer applies what it finds.'
    ),
    schema=tools.schema(
        {
            'plan_ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Plan ids; may be empty.'},
            'document_id': {'type': 'integer', 'description': 'A file id from <documents>, or 0.'},
        }
    ),
    run=check_values,
)
