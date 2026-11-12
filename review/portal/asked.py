"""What one link asks, worked out now from the request's asks and what the owners hold (plan.md §5.8; L.6, L81–L94;
B43, C35). The payload shows exactly this and every write is checked against it: one allowlist, built on
`rules.requests.carries` (§5.8: "the one rule for what a link asks").

Blanks and gaps read stored values only (a pending answer does not fill a slot), so what a scope asks holds still
while the client answers it, and reads missing again once a link ends (L.6).
- **Intake**: every question `carries` names, hidden ones included: a question shows when its rule passes over the
  stored answers and the client's own, and the page re-checks rules whose question it also asks as they type (L83).
  The blocks (contacts, coverage, lines, bor, files) are asked by name.
- **Census**: for each live person, the columns `carries` names among the columns the portal asks (`census.client_view
  .columns`: never SSN, OQ16); a person a client added through this request is asked their own columns whole, or the
  required ones on a "required gaps" ask. Anyone with nothing asked is left out. People can be added once the page
  shows people (census scope other than none; their names need the PIN, OQ80).
- **Files**: the census file; the document slots named, the checklist's missing files on a "missing" ask, and the
  compliance files when the intake's `files` block is asked (old COMPLIANCE_TYPES).
"""

from collections import namedtuple

from census import client_view as census_view
from census import facts as census_facts
from census import fields
from intake import checklist as intake_checklist
from intake import client_view as intake_view
from intake import form, values
from intake.checklist_words import COMPLIANCE
from intake.models import Intake

from ..rules import asks as ask_rules
from ..rules.requests import carries

Asked = namedtuple(
    'Asked',
    'intake_keys blocks people columns needed census_file add_people documents intake rules overlay',
)


def _would_need(key, rules):
    """Needed when shown: the deal's own rule, else every quote-blocking and conditional question (B6)."""
    rule = values.rule_of(rules, key)
    return rule == values.REQUIRED if rule else form.BY_KEY[key]['need'] in ('Q', 'C')


def _intake(asks, deal, intake):
    if not (asks.get('intake') or {}):
        return [], []
    held = intake_view.stored(deal, intake)
    rules = (intake.rules if intake else None) or {}
    empty = {f'intake:{key}' for key in form.KEYS if values.blank(held.get(key))}
    missing = {ref for ref in empty if _would_need(ref.split(':', 1)[1], rules)}
    keys = [key for key in form.KEYS if carries(asks, f'intake:{key}', missing=missing, blank=empty)]
    blocks = [block for block in ask_rules.INTAKE_BLOCKS if carries(asks, f'intake:block:{block}')]
    return keys, blocks


def overlay(deal, intake, link, blank):
    """The answers a question's rule reads: the stored ones with the client's pending answers over them."""
    client = (intake.client if intake else None) or {}
    out = {} if blank else dict(intake_view.stored(deal, intake))
    for key in form.KEYS:
        entry = client.get(key)
        if (entry and entry.get('status') == 'pending') and (not blank or entry.get('link') == link.id):
            out[key] = entry.get('value')
    return out


def _person_columns(asks, member, cols, needed, added):
    census = asks.get('census') or {}
    kind_cols = cols[member.kind]
    if added:
        wanted = census.get('columns') or kind_cols
        if census.get('scope') == 'missing':
            wanted = [key for key in wanted if key in needed[member.kind]]
        return [key for key in kind_cols if key in wanted]
    named = [cell[1] for cell in census.get('cells') or [] if str(cell[0]) == str(member.id)]
    candidates = [key for key in fields.KEYS if (key in kind_cols or key in named) and key not in fields.SSN_KEYS]
    empty = {f'census:{member.id}:{key}' for key in candidates if not (member.values or {}).get(key)}
    missing = {ref for ref in empty if ref.rsplit(':', 1)[1] in needed[member.kind]}
    return [key for key in candidates if carries(asks, f'census:{member.id}:{key}', missing=missing, blank=empty)]


def _census(asks, deal, link, link_ids, blank):
    if (asks.get('census') or {}).get('scope', 'none') in ('none', ''):
        return [], {}, {}
    needed = census_facts.needed(deal)
    cols = census_view.columns(deal, needed)
    people, columns = [], {}
    for member in census_view.people(deal.id, link_ids, link.id, blank=blank):
        wanted = _person_columns(asks, member, cols, needed, census_view.added(member))
        if wanted or census_view.added(member):
            people.append(member)
            columns[member.id] = wanted
    return people, columns, needed


def _missing_files(deal):
    """The checklist's missing files, as `doc:<kind>` refs (`documents.missing`)."""
    from intake.selectors import gate_of

    rows = gate_of(deal)['checklist']['items']
    return {f'doc:{row["kind"]}' for row in rows if row.get('satisfy') == 'document' and row['status'] == 'missing'}


def _documents(asks, deal, blocks):
    documents = asks.get('documents') or {}
    missing = _missing_files(deal) if documents.get('missing') else set()
    slots = list(documents.get('slots') or [])
    slots += sorted(ref.split(':', 1)[1] for ref in missing if ref.split(':', 1)[1] in ask_rules.DOCUMENT_KINDS)
    if 'files' in blocks:
        slots += [kind for kind, _label in COMPLIANCE]
    return list(dict.fromkeys(slots))


def asked(link, request, deal, *, link_ids=()):
    """Asked(...) for `link` now. `link_ids`: every link on its request (whose added people it shares)."""
    asks = request.asks or {}
    blank = bool(link.blank)
    intake = Intake.objects.filter(deal_id=deal.id).first()
    keys, blocks = _intake(asks, deal, intake)
    people, columns, needed = _census(asks, deal, link, link_ids or (link.id,), blank)
    census_on = (asks.get('census') or {}).get('scope', 'none') not in ('none', '')
    return Asked(
        intake_keys=keys,
        blocks=blocks,
        people=people,
        columns=columns,
        needed=needed,
        census_file=carries(asks, 'census:file'),
        add_people=census_on,
        documents=_documents(asks, deal, blocks),
        intake=intake,
        rules=(intake.rules if intake else None) or {},
        overlay=overlay(deal, intake, link, blank) if keys else {},
    )


def refs(found):
    """Every answer ref this link takes (the save's allowlist)."""
    out = {f'intake:{key}' for key in found.intake_keys}
    out |= {f'intake:block:{block}' for block in found.blocks if block in ('contacts', 'coverage', 'lines')}
    out |= {f'census:{member_id}:{key}' for member_id, keys in found.columns.items() for key in keys}
    return out


def member_ids(found):
    return {member.id for member in found.people}


def checklist_note(intake, kind):
    """The note a person left the client on a checklist file ("Still needed ▸", L122), or ''."""
    stored = (intake.checklist if intake else None) or {}
    for key, item_kind in intake_checklist.KINDS.items():
        if item_kind == kind:
            return (stored.get(key) or {}).get('client_note') or ''
    return ''
