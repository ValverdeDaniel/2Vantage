"""The marketing checklist (plan.md §5.2, §6.5; B25–B28, O.6 #2). Pure: the deal's facts in, the card out.

The size tier comes from the one headcount (`intake.providers.headcount`, filled by quotes' `enrolled_headcount`;
OQ53: 51 or more enrolled is large): micro (10 or fewer), small (11–50), mid (51–99), 100+ (B25). Each item is auto
(derived), attested (a person ticks it) or a document (a file of its kind, an "On file" tick, or the signed in-app
form), in old Vantage's order (891f1b3 `market/marketing_checklist.py`):
- coverage intent (auto: confirmed; never waived) and census (auto: Census OK; never waived);
- COBRA (attested; the Census tab ticks the same entry, C25), salary & occupation (attested; a life or disability line
  requested);
- the medical questionnaire (document; medical marketed; label by tier; the form from questionnaire's provider, slice
  42) and the stop-loss disclosure (an "Optional" offer until a form is picked);
- the renewal and invoice, by line (each line in force and shopped holds its copy, or one file says nothing about
  lines); both read "Not needed" on their own when nothing is in force or nothing in force is shopped (D-183);
- claims (100+ enrolled, or level- or self-funded: coverage, the current plans, or the intake answer "self-funded" —
  B26's fix).
A person's requirement overrides an item: Waived ("Not needed") takes it off the gate; Required ("Still needed ▸",
with a note the client sees) puts it back as not done even when satisfied. Custom asks are Review's asks (slice 53).

`Intake.checklist` holds one entry per item a person touched: `{checked, by, at, note, requirement, client_note,
form_key}` (§6.5); an item never touched has no entry and reads unchecked.
"""

from collections import namedtuple

from . import checklist_words as words

COVERAGE_INTENT, CENSUS = 'coverage_intent', 'census'
COBRA, SALARY = 'cobra', 'salary_occupation'
QUESTIONNAIRE, STOP_LOSS = 'medical_questionnaire', 'stop_loss_disclosure'
RENEWAL, INVOICE, CLAIMS = 'renewal', 'invoice', 'claims'

FIXED = (COVERAGE_INTENT, CENSUS)  # derived: never ticked, never waived (the escape is Market anyway, B34)
ATTESTED = (COBRA, SALARY, QUESTIONNAIRE, STOP_LOSS, RENEWAL, INVOICE, CLAIMS)  # items a person ticks or overrides
LINE_ITEMS = (RENEWAL, INVOICE)
AUTO, ATTEST, DOCUMENT = 'auto', 'attest', 'document'
KINDS = {
    QUESTIONNAIRE: 'questionnaire',
    STOP_LOSS: 'stop_loss',
    RENEWAL: 'renewal',
    INVOICE: 'invoice',
    CLAIMS: 'claims',
}
LABELS = {
    COVERAGE_INTENT: words.COVERAGE_INTENT_LABEL,
    CENSUS: words.CENSUS_LABEL,
    COBRA: words.COBRA_LABEL,
    SALARY: words.SALARY_LABEL,
    QUESTIONNAIRE: words.QUESTIONNAIRE[words.GE100][0],
    STOP_LOSS: words.STOP_LOSS_LABEL,
    RENEWAL: words.RENEWAL_LABEL,
    INVOICE: words.INVOICE_LABEL,
    CLAIMS: words.CLAIMS_LABEL,
}
REQUIRED, WAIVED = 'required', 'waived'
REQUIREMENTS = ('', REQUIRED, WAIVED)  # '' = the item's own rule; 'waived' reads "Not needed"
FORM_NONE = 'none'  # the old app's "No fillable form — upload only" (B22); read as `upload`
FORM_UPLOAD, FORM_AUTO = 'upload', 'auto'  # the stored form choices besides a form key (G4; questionnaire/forms)
FORM_SOURCES = ('producer', 'band')  # who set a stored form choice: a person, or the band frozen by a first write
NOTE_LIMIT = 300
SALARY_LINES = {'basic_life_add', 'voluntary_life', 'std', 'ltd'}  # old LIFE_DISABILITY_LINES
LEVEL_OR_SELF = {'level_funded', 'self_funded'}

# What the rules read about one deal. `intent` is the coverage card (`selectors.card`); `kinds` the kinds of its live
# files; `funding` every funding the deal records (coverage rows, current plans); `self_funded` the intake answer;
# `forms` questionnaire's provider ({item: {form, source, signed, …}}); `stored` the row's `checklist`.
Facts = namedtuple('Facts', 'headcount census_ok intent requested_lines kinds funding self_funded forms stored')


def tier(count):
    """The size tier of an enrolled headcount (B25): at 50 a group is small, at 51 mid (OQ53)."""
    count = count or 0
    if count >= 100:
        return words.GE100
    if count >= 51:
        return words.MID
    if count >= 11:
        return words.SMALL
    return words.MICRO


def entry_of(checklist, key):
    """The stored entry of one item, or {}."""
    found = (checklist or {}).get(key)
    return dict(found) if isinstance(found, dict) else {}


def ticked(entry, checked, user_id, at, note=None):
    """The entry after a person ticks (or unticks) it, or None when nothing changes. Who and when follow the tick;
    the requirement stays. `note` (given with the tick, as the old door took it) replaces the note."""
    after = {key: value for key, value in entry.items() if key not in ('checked', 'by', 'at')}
    if checked and entry.get('checked'):
        after.update({key: entry[key] for key in ('checked', 'by', 'at') if key in entry})  # already ticked: kept
    elif checked:
        after.update({'checked': True, 'by': user_id, 'at': at})
    if note is not None:
        after.pop('note', None)
        if note:
            after['note'] = note
    return None if after == entry else after


def required_as(entry, requirement, client_note=''):
    """The entry after a person sets an item's requirement, or None when nothing changes. The client's note goes
    with "Still needed" only; Waived and Undo ('') clear it."""
    after = {key: value for key, value in entry.items() if key not in ('requirement', 'client_note')}
    if requirement:
        after['requirement'] = requirement
    if requirement == REQUIRED and client_note:
        after['client_note'] = client_note
    return None if after == entry else after


def item_state(key, entry, by_name=''):
    """One item's tick as a screen shows it: {key, label, checked, by, by_name, at, requirement} (the Census tab's
    COBRA tick, C25)."""
    return {
        'key': key,
        'label': LABELS[key],
        'checked': bool(entry.get('checked')),
        'by': entry.get('by'),
        'by_name': by_name if entry.get('checked') else '',
        'at': entry.get('at') if entry.get('checked') else None,
        'requirement': entry.get('requirement') or '',
    }


def _form(key, entry, forms):
    """The in-app form a questionnaire row uses, as questionnaire's provider says (slice 42), else the pick stored on
    the entry: {form_key, form_source, signed, needed}. `needed`: the item asks for something — a form, or "upload
    only" (G4: on the stop-loss row `upload` makes the disclosure required with no fillable form)."""
    found = (forms or {}).get(key) or {}
    picked = entry.get('form_key') or ''
    stored_form = '' if picked in ('', FORM_NONE, FORM_UPLOAD, FORM_AUTO) else picked
    form_key = found.get('form') or ('' if found else stored_form)
    source = found.get('source') or ('producer' if picked else '')
    needed = found['needed'] if 'needed' in found else bool(form_key or picked in (FORM_NONE, FORM_UPLOAD))
    return {'form_key': form_key, 'form_source': source, 'signed': bool(found.get('signed')), 'needed': needed}


def _definitions(f, tier_key):
    """(key, label, detail, how it is satisfied, whether it applies) per item, in the card's order."""
    requested = set(f.requested_lines or [])
    q_label, q_detail = words.QUESTIONNAIRE[tier_key]
    funded = bool(LEVEL_OR_SELF & set(f.funding or ())) or f.self_funded == 'Yes'
    stale = bool((f.intent or {}).get('stale'))
    claims = words.CLAIMS_DETAIL_LARGE if tier_key == words.GE100 else words.CLAIMS_DETAIL_FUNDED
    return [
        (COVERAGE_INTENT, LABELS[COVERAGE_INTENT],
         words.COVERAGE_INTENT_STALE if stale else words.COVERAGE_INTENT_DETAIL, AUTO, True),
        (CENSUS, LABELS[CENSUS], words.CENSUS_DETAIL.format(geo=words.GEO[tier_key]), AUTO, True),
        (COBRA, LABELS[COBRA], words.COBRA_DETAIL, ATTEST, True),
        (SALARY, LABELS[SALARY], words.SALARY_DETAIL, ATTEST, bool(SALARY_LINES & requested)),
        (QUESTIONNAIRE, q_label, q_detail, DOCUMENT, 'medical' in requested or not requested),
        (STOP_LOSS, LABELS[STOP_LOSS], words.STOP_LOSS_DETAIL, DOCUMENT, True),
        (RENEWAL, LABELS[RENEWAL], words.RENEWAL_DETAIL, DOCUMENT, True),
        (INVOICE, LABELS[INVOICE], words.INVOICE_DETAIL, DOCUMENT, True),
        (CLAIMS, LABELS[CLAIMS], claims, DOCUMENT, tier_key == words.GE100 or funded),
    ]  # fmt: skip


def items(f):
    """The checklist's rows for one deal, in order (B26, B27)."""
    tier_key = tier(f.headcount)
    intent = f.intent or {}
    rows, counts = intent.get('rows') or [], intent.get('counts') or {}
    all_answered = bool(rows) and not counts.get('unanswered')
    nothing_in_force = all_answered and not counts.get('in_force')
    needing = [row for row in rows if row.get('needs_documents')]
    # "Nothing shopped" only once somebody said: every line answered, and lines to quote or a confirmation.
    none_shopped = all_answered and not needing and bool(f.requested_lines or intent.get('confirmed'))
    found = []
    for key, label, detail, satisfy, applies in _definitions(f, tier_key):
        entry = entry_of(f.stored, key)
        requirement = '' if key in FIXED else (entry.get('requirement') or '')
        forced, waived = requirement == REQUIRED, requirement == WAIVED
        auto_waived = key in LINE_ITEMS and (nothing_in_force or none_shopped) and not requirement
        if auto_waived:
            waived = True
            detail = words.NOT_IN_FORCE_DETAIL if nothing_in_force else words.NOT_SHOPPED_DETAIL
        if not applies and not forced:
            continue
        form = _form(key, entry, f.forms)
        optional = key == STOP_LOSS and not form['needed'] and not forced
        kind = KINDS.get(key, '')
        has_document = bool(kind) and kind in f.kinds
        if key in LINE_ITEMS and needing:
            has_document = all((row.get('documents') or {}).get(kind) for row in needing)
        attested = bool(entry.get('checked'))
        if satisfy == AUTO:
            done = bool(intent.get('confirmed')) if key == COVERAGE_INTENT else bool(f.census_ok)
        elif satisfy == DOCUMENT:
            done = has_document or attested or form['signed']
        else:
            done = attested
        done = done and not forced
        status = 'waived' if waived else 'offer' if optional and not done else 'done' if done else 'missing'
        found.append(
            {
                'key': key,
                'label': label,
                'detail': detail,
                'satisfy': satisfy,
                'kind': kind,
                'has_document': has_document,
                'attested': attested,
                'by': entry.get('by') if attested else None,
                'at': entry.get('at') if attested else None,
                'note': entry.get('note') or '',
                'done': done,
                'waived': waived,
                'auto_waived': auto_waived,
                'waived_reason': ('not_in_force' if nothing_in_force else 'not_shopped') if auto_waived else '',
                'forced': forced,
                'optional': optional,
                'client_note': entry.get('client_note') or '',
                'status': status,
                **form,
            }
        )
    return found


def meter(rows):
    """{required, done, missing, all_clear}: the items the gate counts (neither waived nor an optional offer)."""
    counted = [row for row in rows if not row['waived'] and not row['optional']]
    done = sum(1 for row in counted if row['done'])
    return {'required': len(counted), 'done': done, 'missing': len(counted) - done, 'all_clear': done == len(counted)}


def card(f, headcount=None):
    """The checklist card (B25–B27): the tier and its headcount, the rows, and the meter. `headcount` is the provider's
    {count, source, estimate}."""
    tier_key = tier(f.headcount)
    rows = items(f)
    known = headcount or {}
    return {
        'tier': tier_key,
        'tier_label': words.TIER_LABELS[tier_key],
        'enrolled': f.headcount,
        'estimate': bool(known.get('estimate')),
        'headcount_source': known.get('source') or '',
        'geo': words.GEO[tier_key],
        'items': rows,
        **meter(rows),
    }
