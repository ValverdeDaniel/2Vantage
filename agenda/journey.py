"""The journey's milestones and progress (I69, I120; plan.md §5.9). Pure: from the same steps and facts as the next
step, so the stepper, the progress bar and the Agenda never disagree.

Milestones, in order: intake ready, enrollment in, sent to market (Get to Market); quotes in, proposal built, proposal
issued, sold, commission entered (Quote to Close). Each is done, todo or skipped. A quote-first deal skips the intake
and market milestones it went past (quotes in before it was ready or marketed), and a deal sold without an issued
proposal skips that one: a skipped milestone never counts and is never shown as "skipped" to anyone (M40); progress
is milestones done over those that apply (OQ94's default meaning).
"""

from . import catalogue

DONE, TODO, SKIPPED = 'done', 'todo', 'skipped'


def _step_done(steps, key):
    return any(step['key'] == key and step['state'] == 'done' and not step.get('done_anyway') for step in steps)


def journey(facts, unmarked_steps):
    """[{key, label, group, state}] with `current` on the first milestone still to do."""
    intake = facts.get('intake') or {}
    census = facts.get('census') or {}
    quotes = facts.get('quotes') or {}
    deal = facts.get('deal') or {}
    quotes_in = (quotes.get('quotes') or 0) > 0
    sold = bool(deal.get('sold'))
    marketed = intake.get('marketed_at') is not None
    issued = bool((facts.get('proposals') or {}).get('latest'))
    done = {
        'intake_ready': marketed or intake.get('ready_state') in ('ready', 'submitted'),
        'enrollment_in': (census.get('employees') or 0) > 0 or (quotes_in and not quotes.get('unpriced')),
        'marketed': marketed,
        'quotes_in': quotes_in,
        'built': issued or _step_done(unmarked_steps, 'build_proposal'),
        'issued': issued,
        'sold': sold,
        'commission': sold and _step_done(unmarked_steps, 'commission'),
    }
    skipped = {
        'intake_ready': quotes_in or sold,
        'marketed': quotes_in or sold,
        'built': sold,
        'issued': sold,
    }
    out, current = [], None
    for key, label, group in catalogue.MILESTONES:
        state = DONE if done[key] else SKIPPED if skipped.get(key) else TODO
        if state == TODO and current is None:
            current = key
        out.append({'key': key, 'label': label, 'group': group, 'state': state, 'current': False})
    for row in out:
        row['current'] = row['key'] == current
    return out


def progress(milestones):
    """{done, total, pct} over the milestones that apply."""
    counted = [row for row in milestones if row['state'] != SKIPPED]
    done = sum(1 for row in counted if row['state'] == DONE)
    total = len(counted)
    return {'done': done, 'total': total, 'pct': round(done / total * 100) if total else 100}
