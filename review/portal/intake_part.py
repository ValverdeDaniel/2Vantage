"""The intake part of a link's page (plan.md §8.20; L83–L86, L108; B43; OQ84). Allowlisted: a question's words, its
rule, the value the page shows (a pending answer over the stored one; on a blank link only the link's own), its
compare-and-set base, whether it is on file (locked) or read by us; the blocks with what the deal holds in the same
shape; a question's `help` is the deal's own note to the client when a person left one (B37, L122; slice 57). Never
commission, `on_proposal`, the Keep / Leave off decisions, sources, names of who did what, or files.
"""

from deals import contacts as contact_rules
from deals import lines
from intake import client_view as intake_view
from intake import form, readiness, values
from intake.services.rules import note_of as rule_note
from intake.status import notes

from ..rules import portal as portal_rules

QUESTION = ('key', 'label', 'type', 'options', 'hint', 'help')


def _needed(key, rules):
    rule = values.rule_of(rules, key)
    return rule == values.REQUIRED if rule else form.BY_KEY[key]['need'] in ('Q', 'C')


def _field(question, view, source, stored, found, carried, blank):
    shown, base, colleague = view
    on_file = not portal_rules.editable(source, stored, reopened=question['key'] in found.reopened)
    rule = question.get('shown_when')
    note = rule_note(found.rules.get(question['key']))  # the deal's note to the client, in place of our help (B37)
    return {
        **{key: question.get(key, '' if key != 'options' else []) for key in QUESTION},
        **({'help': note} if note else {}),
        'needed': _needed(question['key'], found.rules),
        'value': '' if (on_file and blank) else shown,
        'base': base,
        'locked': on_file,
        'we_read': '' if blank else portal_rules.we_read(source, stored),
        'by_colleague': colleague,
        'shown': values.shown(question, found.overlay),
        'shown_when': rule if rule and rule.get('field') in carried else None,
    }


def _bor(deal, intake):
    signed = bool(intake and intake.bor_signed_at)
    on_file = readiness.bor_on_file(
        intake.bor_signed_at if intake else None,
        list(deal.documents.filter(kind='bor').values_list('id', flat=True)[:1]),
    )
    return {
        'signed': signed,
        'name': intake.bor_name if signed else '',
        'signed_at': intake.bor_signed_at.isoformat() if signed else None,
        'on_file': on_file,
    }


def _block(view):
    shown, base, colleague = view
    return {'value': shown, 'base': base, 'by_colleague': colleague}


def _choices(pairs):
    return [{'key': key, 'label': label} for key, label in pairs]


def section(found, deal, link):
    """{sections: [{key, label, fields}], blocks: {contacts?, coverage?, lines?, bor?}}, or None when nothing is
    asked."""
    if not found.intake_keys and not found.blocks:
        return None
    blank = bool(link.blank)
    intake = found.intake
    views = intake_view.views(deal, intake, link.id, blank=blank)
    held = intake_view.stored(deal, intake)
    sources = (intake.sources if intake else None) or {}
    carried = set(found.intake_keys)
    sections = []
    for key, label in form.SECTIONS:
        asked = [q for q in form.QUESTIONS if q['section'] == key and q['key'] in carried]
        if asked:
            fields = [
                _field(q, views[q['key']], sources.get(q['key']), held.get(q['key']), found, carried, blank)
                for q in asked
            ]
            sections.append({'key': key, 'label': label, 'fields': fields})
    blocks = {}
    if 'contacts' in found.blocks:
        roles = [(key, contact_rules.label(key)) for key in contact_rules.CLIENT_SIDE]
        blocks['contacts'] = {**_block(views[intake_view.CONTACTS]), 'roles': _choices(roles)}
    if 'coverage' in found.blocks:
        blocks['coverage'] = {
            **_block(views[intake_view.COVERAGE]),
            'lines': _choices((line['key'], line['label']) for line in lines.LINES),
            'funding': _choices(lines.FUNDING),
        }
    if 'lines' in found.blocks:
        blocks['lines'] = {
            **_block(views[intake_view.LINES]),
            'lines': _choices((line['key'], line['label']) for line in lines.LINES),
            'note': notes({}, deal.requested_lines)['census'] or '',
        }
    if 'bor' in found.blocks:
        blocks['bor'] = _bor(deal, intake)
    return {'sections': sections, 'blocks': blocks}
