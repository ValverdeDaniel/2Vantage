"""quotes' re-check (plan.md §10.4, §10.7; D40, D93, E77, F66, OQ28; slice 22; the old ai/flag_check.py at 891f1b3):
which plan values Claude reads again, and what it proposes from its verdicts. ai's `recheck` job calls these through
`registry.checkers['quotes']`; a person applies the change set (`services.recheck_apply`).

- `claims(deal, scope)`: the open warnings (`review_rules.open_warning`, OQ28) on the deal's plans that came from a
  file — the values named (`refs`), those on some plans, those read from some files, or all of them — each with its
  file, page or cell, and a label of plan and field (never a person's details). A value no longer flagged is left out.
- `build_changes(deal, claims, verdicts, extra)`: one item per value, so each row of the card has its own tick:
  - Claude agrees: `confirm`, ticked: applying approves it as the person who pressed Apply (`via: recheck`, E77);
  - the file prints something else: `set_values` old → new, ticked unless Claude was unsure (a sold plan's is
    unticked, frozen), the new value cleaned as if typed; a "difference" that is only formatting is an agreement;
  - not found on its page, or not checked (no page in a long file, a cost cap): listed in `unverified`, still
    flagged, nothing to apply.
"""

from rest_framework.exceptions import ValidationError

from documents.models import Document
from documents.review_rules import open_warning

from . import fields
from .models import Plan
from .reader import rules
from .services.review import NO_FILES, NO_PLANS, parse_refs

NOT_FOUND = 'not found on its page'
NOT_A_VALUE = 'the file prints “{found}”, which is not a value for {label}'
SOLD = 'Sold: left as sold'
UNSURE = 'Claude was unsure of this fix.'
SILENT = 'Claude did not report on it.'


def _ids(raw, name, sentence):
    try:
        ids = sorted({int(item) for item in raw})
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: [sentence]}) from exc
    if not ids:
        raise ValidationError({name: [sentence]})
    return ids


def claims(deal, scope):
    """[{ref, doc, page, cell, label, value}] in board order; 400 for plans or files not the deal's."""
    plans = Plan.objects.filter(deal=deal).order_by('line', 'sort_order', 'id')
    wanted = parse_refs(scope['refs']) if scope.get('refs') else None
    if wanted is not None:
        plans = plans.filter(id__in=list(wanted))
    if scope.get('plan_ids') is not None:
        plan_ids = _ids(scope['plan_ids'], 'plan_ids', NO_PLANS)
        if Plan.objects.filter(deal=deal, id__in=plan_ids).count() != len(plan_ids):
            raise ValidationError({'plan_ids': [NO_PLANS]})
        plans = plans.filter(id__in=plan_ids)
    documents = None
    if scope.get('document_ids') is not None:
        documents = set(_ids(scope['document_ids'], 'document_ids', NO_FILES))
        if Document.all_objects.filter(deal=deal, id__in=documents).count() != len(documents):
            raise ValidationError({'document_ids': [NO_FILES]})
    out = []
    for plan in plans:
        for key in fields.keys_for(plan.line):
            source = plan.sources.get(key)
            if key not in plan.values or not open_warning(source) or not (source or {}).get('doc'):
                continue
            if wanted is not None and key not in wanted.get(plan.id, ()):
                continue
            if documents is not None and source['doc'] not in documents:
                continue
            out.append(
                {
                    'ref': f'plan:{plan.id}:{key}',
                    'doc': source['doc'],
                    'page': source.get('page') or None,
                    'cell': source.get('cell') or '',
                    'label': f'{plan.carrier} {plan.name} — {fields.BY_KEY[key]["label"]}',
                    'value': str(plan.values[key]),
                }
            )
    return out


def _split(ref):
    _kind, _, rest = ref.partition(':')
    plan_id, _, key = rest.partition(':')
    return int(plan_id), key


def _verdict(plan, key, verdict):
    """('agree' | 'differs' | 'not_found', new value or None, why for not found)."""
    kind, found = verdict['verdict'], verdict['found_value'].strip()
    if kind != 'differs':
        return kind, None, NOT_FOUND
    if not found:
        return 'not_found', None, NOT_FOUND
    new, _why = rules.clean(key, found)
    if new is None:
        return 'not_found', None, NOT_A_VALUE.format(found=found[:80], label=fields.BY_KEY[key]['label'])
    if str(new) == str(plan.values.get(key)):
        return 'agree', None, ''  # formatting is not a difference
    return 'differs', new, ''


class Changes:
    def __init__(self):
        self.items, self.unverified = [], []

    def item(self, op, plan, value, tick, why=''):
        self.items.append(
            {
                'id': f'i{len(self.items) + 1}',
                'op': op,
                'plan': plan.id,
                'line': plan.line,
                'role': plan.role,
                'carrier': plan.carrier,
                'name': plan.name,
                'plan_number': plan.plan_number,
                'values': [value],
                'tick': tick,
                'stale': False,
                'frozen': bool(plan.sold),
                'why': why,
            }
        )

    def miss(self, claim, plan, key, reason):
        self.unverified.append(
            {
                'ref': claim['ref'],
                'plan': plan.id,
                'plan_label': f'{plan.carrier} {plan.name}',
                'key': key,
                'label': fields.BY_KEY[key]['label'],
                'value': claim['value'],
                'doc': claim['doc'],
                'page': claim['page'],
                'reason': str(reason)[:200],
            }
        )


def build_changes(deal, claims_checked, verdicts, extra):
    """The re-check's change set (D.6's shape; `kind: recheck`)."""
    extra = dict(extra)
    not_asked = extra.pop('not_asked', {})
    ids = {_split(claim['ref'])[0] for claim in claims_checked}
    plans = {plan.id: plan for plan in Plan.objects.filter(deal=deal, id__in=ids)}
    out = Changes()
    for claim in claims_checked:
        plan_id, key = _split(claim['ref'])
        plan, verdict = plans.get(plan_id), verdicts.get(claim['ref'])
        if plan is None:
            continue
        if verdict is None:
            out.miss(claim, plan, key, not_asked.get(claim['ref']) or SILENT)
            continue
        kind, new, why = _verdict(plan, key, verdict)
        if kind == 'not_found':
            out.miss(claim, plan, key, why if why != NOT_FOUND else (verdict['note'] or NOT_FOUND))
            continue
        value = {
            'key': key,
            'label': fields.BY_KEY[key]['label'],
            'old': claim['value'],
            'new': new if kind == 'differs' else claim['value'],
            'doc': claim['doc'],
            'page': verdict['page'] or claim['page'],
            'cell': claim['cell'],
            'line': '',
            'loc': None,
            'low': UNSURE if kind == 'differs' and verdict['confidence'] == 'low' else None,
            'confidence': verdict['confidence'],
            'note': verdict['note'],
            'why': '',
            'tick': True,
        }
        if kind == 'agree':
            out.item('confirm', plan, value, True)
        else:
            frozen = bool(plan.sold)
            value['tick'] = not frozen and verdict['confidence'] != 'low'
            out.item('set_values', plan, value, value['tick'], SOLD if frozen else '')
    approvals = sum(1 for item in out.items if item['op'] == 'confirm')
    fixes = len(out.items) - approvals
    misses = len(out.unverified)
    findings = [{'text': extra['halted'], 'hard': False}] if extra.get('halted') else []
    return {
        'v': 1,
        'kind': 'recheck',
        'target': 'quotes',
        'documents': sorted({claim['doc'] for claim in claims_checked}),
        'summary': f'{approvals} look right · {fixes} need a fix · {misses} not found',
        'counts': {
            'items': len(out.items),
            'approvals': approvals,
            'fixes': fixes,
            'unverified': misses,
            'unticked': sum(1 for item in out.items if not item['tick']),
            'findings': len(findings),
        },
        'items': out.items,
        'unverified': out.unverified[:200],
        'findings': findings,
        'landed': {'plan_ids': [], 'areas': []},
        **extra,
    }


def open_flags(deal):
    """The open warnings on the deal's live plans (their stored `flags`), for the strip's re-check offer (E80)."""
    from django.db.models import Sum

    return Plan.objects.filter(deal=deal).aggregate(total=Sum('flags'))['total'] or 0


def checker():
    from ai.registry import Checker

    from . import revert_read
    from .services import recheck_apply

    return Checker(
        owner='quotes', claims=claims, build_changes=build_changes, apply=recheck_apply.apply, undo=revert_read.undo
    )
