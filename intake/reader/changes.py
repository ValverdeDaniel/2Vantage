"""An intake read's change set (plan.md §5.2, §10.5; B39's rule, B40, D60, D61, D112; slice 51).

What using the read would change, as items a person ticks (D.6's shape), waiting in Intake's review (O.3.3):
- `answer`: one per question the file answers with something new: the cleaned value (the form's one cleaner, B.5),
  the answer it replaces, its file and page or cell, and Claude's doubt. An equal answer is not listed (D60). An answer
  a person stands behind (typed, entered for the client, the client's own, or approved) arrives unticked and says so,
  and so does one Claude was unsure of (§10.5): never written over unless a person ticks it (D61; B39's rule);
- `coverage`: a line of coverage the deal lacks, or the blanks of the line it has (the old reader "fills coverage
  blanks by line"); carrier and funding are left out where the line has current plans, which own them (§6.5);
- `contact`: a contact the client does not have yet (by email, else by name).
A value the form cannot take becomes a finding, never a failed read (D58).
"""

from deals import lines as line_vocab
from deals.models import Contact
from documents.review_rules import is_approved

from .. import form, values
from ..models import CurrentCoverage, Intake
from ..selectors import answers_of
from ..services.coverage import FUNDING as FUNDING_KEYS
from ..services.coverage import has_plans
from ..values import parse_date

KEPT = ('failed_parts', 'left_out_pages', 'model', 'cost_usd', 'estimate_usd', 'partial', 'halted')
HELD = {
    'typed': 'typed by a person',
    'relay': 'entered for the client',
    'client': "the client's own answer",
}
COVERAGE_LABELS = {'carrier': 'Carrier', 'funding': 'Funding', 'renewal_date': 'Renewal date'}
FUNDING_LABELS = dict(line_vocab.FUNDING)
EMAIL = r'[^@\s]+@[^@\s]+\.[^@\s]+'


def same(stored, read):
    """Whether a stored answer already says what was read: blanks match, a list matches its list."""
    if isinstance(stored, list) or isinstance(read, list):
        return list(stored or []) == list(read or [])
    return str(stored or '').strip() == str(read or '').strip()


def _plural(count, one, many):
    return f'{count} {one if count == 1 else many}'


def _why_held(entry):
    if is_approved(entry):
        return 'Left alone: a person approved the answer on the deal. Tick it to use the read anyway.'
    said = HELD.get(entry.get('origin'))
    return f'Left alone: the answer on the deal was {said}. Tick it to use the read anyway.' if said else ''


def answer_items(deal, fields, findings):
    """One item per answer in `fields` ({key: {value, doc, page, cell, low, dictated?}}) that would change the deal,
    in the form's order. A dictated value (the producer said it in a chat, B39) is theirs to give: ticked."""
    intake = Intake.objects.filter(deal=deal).first()
    answers, sources = answers_of(deal, intake), dict(intake.sources) if intake else {}
    items = []
    for key in form.KEYS:
        read = fields.get(key)
        if not read:
            continue
        question = form.BY_KEY[key]
        value, error = values.clean_value(question, read['value'])
        if error:
            findings.append({'text': f'Not used: {error}.', 'hard': False})
            continue
        old = answers.get(key)
        if value in ('', None, []) or same(old, value):
            continue
        why = ''
        if not read.get('dictated'):
            why = _why_held(sources.get(key) or {}) if not values.blank(old) else ''
            if not why and read['low'] and not read.get('proposed'):  # a chat's proposal is flagged, not unticked
                why = f'{read["low"]} Tick it to use it.'
        items.append(
            {
                'id': f'answer:{key}',
                'op': 'answer',
                'key': key,
                'label': question['label'],
                'section': question['section'],
                'new': value,
                'old': None if values.blank(old) else old,
                'doc': read.get('doc'),
                'page': read.get('page'),
                'cell': read.get('cell'),
                'low': read.get('low'),
                'dictated': bool(read.get('dictated')),
                'why': why,
                'tick': not why,
            }
        )
    return items


def _coverage_values(deal, read, findings):
    """[{key, label, new}] the read gives a line, cleaned; carrier and funding only where no current plans own them."""
    owned = has_plans(deal.id, read['line'])
    out = []
    for key in ('carrier', 'funding', 'renewal_date'):
        new = read.get(key) or ''
        if not new or (owned and key != 'renewal_date'):
            continue
        if key == 'funding' and new not in FUNDING_KEYS:
            continue
        shown = FUNDING_LABELS.get(new, new)
        if key == 'renewal_date':
            parsed = parse_date(new)
            if parsed is None:
                findings.append({'text': f'Not used: a renewal date the form cannot read ("{new}").', 'hard': False})
                continue
            new, shown = parsed.isoformat(), f'{parsed.month:02d}/{parsed.day:02d}/{parsed.year}'
        out.append({'key': key, 'label': COVERAGE_LABELS[key], 'new': new[:200], 'shown': shown[:200]})
    return out


def _stored(row, key):
    value = getattr(row, key)
    return value.isoformat() if hasattr(value, 'isoformat') else (value or '')


def coverage_items(deal, rows_read, findings):
    """One item per line in `rows_read` ([{line, carrier, funding, renewal_date, doc?, page?}]) that adds a line or
    fills a blank."""
    first = {}
    for row in CurrentCoverage.objects.filter(deal=deal).order_by('sort_order', 'id'):
        first.setdefault(row.line, row)
    items = []
    for read in rows_read:
        line = read['line']
        if line not in line_vocab.BY_KEY:
            continue
        found = _coverage_values(deal, read, findings)
        row = first.get(line)
        if row is not None:
            found = [{**value, 'old': None} for value in found if not _stored(row, value['key'])]
        if not found:
            continue
        items.append(
            {
                'id': f'coverage:{line}',
                'op': 'coverage',
                'line': line,
                'label': line_vocab.BY_KEY[line]['label'],
                'coverage': row.id if row is not None else None,
                'values': found,
                'doc': read.get('doc'),
                'page': read.get('page'),
                'tick': True,
            }
        )
    return items


def _contacts(deal, merged, findings):
    import re

    from deals import contacts as contact_vocab

    held = list(Contact.objects.filter(client_id=deal.client_id).values('name', 'email'))
    emails = {str(row['email'] or '').lower() for row in held if row['email']}
    names = {' '.join(str(row['name'] or '').lower().split()) for row in held if row['name']}
    items = []
    for number, read in enumerate(merged['contacts'], start=1):
        email = read['email'] if re.fullmatch(EMAIL, read['email'] or '') else ''
        if read['email'] and not email:
            findings.append({'text': 'Not used: a contact email the form cannot take.', 'hard': False})
        name = ' '.join(read['name'].lower().split())
        if (email and email.lower() in emails) or (name and name in names):
            continue
        role = read['role'] if read['role'] in contact_vocab.LABELS else ''
        items.append(
            {
                'id': f'contact:{number}',
                'op': 'contact',
                'name': read['name'][:200],
                'title': read['title'][:200],
                'email': email[:254],
                'phone': read['phone'][:50],
                'role': role,
                'role_label': contact_vocab.label(role or contact_vocab.HR_ADMIN),
                'doc': read.get('doc'),
                'tick': True,
            }
        )
    return items


def build_changes(deal, user, merged, files, extra):
    """The change set (D.6's shape) of an intake read."""
    findings = []
    items = answer_items(deal, merged['fields'], findings) + coverage_items(deal, merged['coverage'], findings)
    items += _contacts(deal, merged, findings)
    counted = {
        'answers': sum(1 for item in items if item['op'] == 'answer'),
        'coverage': sum(1 for item in items if item['op'] == 'coverage'),
        'contacts': sum(1 for item in items if item['op'] == 'contact'),
        'left_alone': sum(1 for item in items if not item['tick']),
    }
    parts = [
        _plural(counted['answers'], 'intake answer', 'intake answers') if counted['answers'] else '',
        _plural(counted['coverage'], 'coverage line', 'coverage lines') if counted['coverage'] else '',
        _plural(counted['contacts'], 'contact', 'contacts') if counted['contacts'] else '',
    ]
    out = {key: extra[key] for key in KEPT if key in extra}
    out.update(
        v=1,
        target='intake',
        documents=sorted(file.id for file in files),
        summary=' · '.join(part for part in parts if part) or 'Nothing new for Intake in these files',
        counts=counted,
        items=items,
        findings=findings,
    )
    return out
