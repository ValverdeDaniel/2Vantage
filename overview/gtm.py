"""Card 1, Get to Market (plan.md §8.6; M42–M61, M67, M108–M111; old Vantage 891f1b3 `GetToMarketCard.jsx`). Pure:
the deal's facts in, the card out. `payload.py` reads them once.

The card is the intake gate as a requirements board: the readiness badge (Blocked, Ready to market, Sent to market),
"N of M requirements met · <tier>" and the groups in the old order — Coverage & marketing intent, Intake answers,
Census, Medical questionnaire, Stop-loss disclosure, Documents carriers need, Confirmations. A group is met as the old
card met it; its rows are intake's checklist rows as the Intake tab's card shows them, so the controls (On file,
Not needed, Still needed ▸, Undo, ⬆ Attach, the form picker, ＋ Ask) are the same ones and write through the same
doors: intake's checklist, documents' upload, the questionnaire's form choice and review's tray (B30: one set of
controls, two frames). The tier is the checklist's, from the one headcount (`quotes.facts.enrolled_headcount`, C21).

Not here: the old custom asks and "＋ Add request" (M58, M59): no app stores a free-text ask yet (L121 is in no slice's
row; OQ87), so the Documents group lists the carriers' documents only.
"""

from collections import namedtuple

COVERAGE_INTENT = 'coverage_intent'
QUESTIONNAIRE, STOP_LOSS = 'medical_questionnaire', 'stop_loss_disclosure'
DOCUMENT_ITEMS = ('renewal', 'invoice', 'claims')
CONFIRM_ITEMS = ('cobra', 'salary_occupation')
ADVISOR = 'advisor'  # `enrolled_headcount`'s source when the Advisor's counts price the deal

BADGES = {'blocked': 'Blocked', 'ready': 'Ready to market', 'submitted': 'Sent to market'}
TITLES = {
    'coverage': 'Coverage & marketing intent',
    'intake': 'Intake answers',
    'census': 'Census',
    'questionnaire': 'Medical questionnaire',
    'stop_loss': 'Stop-loss disclosure',
    'documents': 'Documents carriers need',
    'confirmations': 'Confirmations',
}
QUOTES_FIRST = 'Quotes came in first — intake, census and the RFP still apply'  # M43
TYPED_COUNTS = 'The Advisor is priced from typed counts — add the census when it arrives'  # M110

# What a row carries to the card: the checklist row's own fields (intake's `checklist.items`).
ROW_KEYS = (
    'key', 'label', 'detail', 'satisfy', 'kind', 'has_document', 'attested', 'note', 'done', 'waived', 'auto_waived',
    'forced', 'optional', 'client_note', 'status', 'form_key', 'form_source', 'signed', 'needed',
)  # fmt: skip

# The deal's facts the card reads. `intake`: intake's payload (`intake.selectors.intake_payload`); `census`: the
# census's stored counts (`census.facts.stored`); `pending`: review's client answers waiting ({intake, census,
# questionnaire?}); `forms`: the questionnaire items ({item: {form, progress, started, signed}}) and `form_labels`
# ({form key: label}); `headcount`: `enrolled_headcount`; `check`: `enrollment_check`; `quotes`: live quotes;
# `refusal`: `deals.rules.client_asks_open`'s sentence, or None.
Facts = namedtuple('Facts', 'intake census pending forms form_labels headcount check quotes refusal')


def _row(row):
    return {key: row.get(key) for key in ROW_KEYS}


def _met(rows):
    return all(row['done'] or row['waived'] for row in rows)


def _received(rows):
    counted = [row for row in rows if not row['waived']]
    return sum(1 for row in counted if row['done']), len(counted)


def quotes_first(quotes, ready_state):
    """Quotes came in before the deal was ready or sent to market (M43; old module 1 "skipped")."""
    return bool(quotes) and ready_state == 'blocked'


def _coverage(item, intent):
    rows = intent.get('rows') or []
    lines = [
        {
            'line': row['line'],
            'label': row.get('label') or row['line'],
            'shopping': bool(row['shopping']),
            'in_force': bool(row['in_force']),
            'on_proposal': bool(row['on_proposal']),
            'guaranteed_to': row.get('rate_guarantee_through'),
        }
        for row in rows
    ]
    shopping = sum(1 for line in lines if line['shopping'])
    return {
        'key': 'coverage',
        'met': bool(item['done']),
        'count': f'{shopping} of {len(lines)} shopping',
        'lines': lines,
        'stale': bool(intent.get('stale')),
        'detail': item.get('detail') or '',
        'confirmed_by': intent.get('confirmed_by') or '',
    }


def _intake(intake, pending):
    ready, readiness = intake['ready'], intake['readiness']
    missing = [gap['label'] for gap in ready['gaps'] if gap['kind'] == 'question']
    met = not missing and ready['contacts_ok'] and ready['bor_on_file']
    return {
        'key': 'intake',
        'met': met,
        'count': f'{readiness["answered"]}/{readiness["needed"]} answered',
        'missing': missing,
        'contacts_ok': ready['contacts_ok'],
        'bor_on_file': ready['bor_on_file'],
        'pending_client': pending.get('intake', 0) or 0,
        'lines': len(intake.get('requested_lines') or []),
    }


def _census(f, census_ok):
    stored = f.census
    employees, dependents = stored.get('employees', 0) or 0, stored.get('dependents', 0) or 0
    typed = (f.headcount or {}).get('source') == ADVISOR and employees == 0
    return {
        'key': 'census',
        'met': bool(census_ok),
        'count': f'{employees} EEs + {dependents} deps',
        'employees': employees,
        'dependents': dependents,
        'required_total': stored.get('required_total', 0) or 0,
        'required_filled': stored.get('required_filled', 0) or 0,
        'errors': stored.get('errors', 0) or 0,
        'pending_client': f.pending.get('census', 0) or 0,
        'enrollment_warning': (f.check or {}).get('warning'),
        'typed_counts': TYPED_COUNTS if typed else None,
        'ask': None if f.refusal else ('roster' if employees else 'file'),  # M49: hidden once asks are closed
    }


def _progress_words(progress, started, signed):
    if not started or not progress:
        return 'not started'
    return f'{progress["filled"]}/{progress["total"]} answered' + (' · signed' if signed else '')


def _form(key, row, f):
    """The questionnaire's or the stop-loss disclosure's group (M50–M56, M108, M109)."""
    found = (f.forms or {}).get(row['key']) or {}
    progress, started, signed = found.get('progress'), bool(found.get('started')), bool(row['signed'])
    offer = key == 'stop_loss' and bool(row['optional'])
    if offer:
        count = 'Optional'
    elif row['waived']:
        count = 'Not needed'
    elif row['form_key']:
        count = f'{progress["filled"]}/{progress["total"]} answered' if started and progress else 'Not started'
    else:
        count = 'Upload only'
    detail = ''
    if row['form_key']:
        mine = key == 'stop_loss' or row['form_source'] == 'producer'
        chosen = ' · chosen by you' if mine else ' · auto by group size'
        label = (f.form_labels or {}).get(row['form_key']) or row['form_key']
        detail = f'{label}{chosen} · {_progress_words(progress, started, signed)}'
    pending = (f.pending or {}).get('questionnaire', 0) or 0 if key == 'questionnaire' else 0
    return {
        'key': key,
        'met': offer or bool(row['done']) or bool(row['waived']),
        'count': count,
        'offer': offer,
        'item': {**_row(row), 'form_detail': detail},
        'pending_client': pending,  # client answers waiting for review (slice 58's `pending.questionnaire`)
    }


def _listed(key, rows, done_word='received'):
    done, counted = _received(rows)
    count = f'{done}/{counted} {done_word}' if done_word else f'{done}/{counted}'
    return {'key': key, 'met': _met(rows), 'count': count, 'items': [_row(row) for row in rows]}


def card(f):
    """{badge, badge_label, quotes_first, met, required, tier, tier_label, headcount, marketed_at, groups}."""
    intake = f.intake
    checklist, ready = intake['checklist'], intake['ready']
    by_key = {row['key']: row for row in checklist['items']}
    groups = []
    if COVERAGE_INTENT in by_key:
        groups.append(_coverage(by_key[COVERAGE_INTENT], intake.get('intent') or {}))
    groups.append(_intake(intake, f.pending or {}))
    groups.append(_census(f, ready['census_ok']))
    if QUESTIONNAIRE in by_key:
        groups.append(_form('questionnaire', by_key[QUESTIONNAIRE], f))
    if STOP_LOSS in by_key:
        groups.append(_form('stop_loss', by_key[STOP_LOSS], f))
    groups.append(_listed('documents', [by_key[key] for key in DOCUMENT_ITEMS if key in by_key]))
    confirm = [by_key[key] for key in CONFIRM_ITEMS if key in by_key]
    if confirm:
        groups.append(_listed('confirmations', confirm, done_word=''))
    for group in groups:
        group['title'] = TITLES[group['key']]
    state = ready['state']
    headcount = f.headcount or {}
    return {
        'badge': state,
        'badge_label': BADGES.get(state, state),
        'quotes_first': QUOTES_FIRST if quotes_first(f.quotes, state) else None,
        'met': sum(1 for group in groups if group['met']),
        'required': len(groups),
        'tier': checklist.get('tier'),
        'tier_label': checklist.get('tier_label') or '',
        'headcount': {
            'value': headcount.get('count'),
            'from': headcount.get('source') or None,
            'estimate': bool(headcount.get('estimate')),
        },
        'marketed_at': (intake.get('marketed') or {}).get('at'),
        'groups': groups,
    }
