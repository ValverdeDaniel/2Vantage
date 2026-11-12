"""One key's report, the packet grid's pills and the stale-ack check (plan.md §7.11, §8.12; K52, K69–K76, K121).

- `report(ctx, key)` → `{key, label, ok, problems, ack}` for any key of the one key space, `packet` (every ticked row's
  problems, each with its row's name, the two-copies warning G110, the deal's) or `draft-<key>` (its attachments'
  problems, the size K121, the deal's). A census file adds the deal's problems; the forms, the cover and UHC's file
  also the enrollment cross-check (K19); a questionnaire is its own check (`questionnaire.check.report`, G64); a paper
  copy someone accepted, a document or the issued proposal has none. Raises `Unknown` for a key the deal does not have.
- `pills(ctx)` → `{cards: {key: {status ready|problems|unsigned, count}}, deal: [problem]}`: every row that can be
  built gets a pill, "Unsigned" included (K52, bug 12); one call, which the page re-asks only when `checks_stamp` moves.
- `stale(ctx, key, ack)`: the fresh report when a download's `ack` no longer matches it (K70); no `ack`, no check.
"""

from questionnaire import rfp_rules
from questionnaire.check import report as questionnaire_report

from .. import drafts
from ..cards import packet as cards
from ..formats import definitions
from ..forms import fill as form_fill
from . import census, deal
from .problems import digest, problem

PACKET, DRAFT = 'packet', 'draft-'
COUNTED = ('form', 'cover', 'census-uhc')  # the files that print the enrolled count (K17, K19)
MAIL_LIMIT = 20_000_000  # about what most mail servers take (K121)
BASE64 = 1.37  # attachments grow about 37% once encoded
KIND_WORDS = {'medical': 'medical questionnaire', 'stop_loss': 'stop-loss disclosure'}
PAPER_KIND = {'questionnaire': 'medical', 'stop_loss': 'stop_loss'}


class Unknown(Exception):
    """A key this deal's RFP has no file for."""


def counted(row):
    return row['key'] in COUNTED or row['section'] == 'census_forms'


def own(ctx, row):
    """A row's own problems, without the deal's."""
    if row['section'] == 'census':
        fmt = definitions.DEFINITIONS[row['format_key']]
        return census.problems(ctx, fmt, row['lens'], row['file_format'])
    if row['section'] == 'census_forms':
        found = census.problems(ctx, form_fill.census_layout(row['variant']), row['lens'])
        return _no_box(ctx, row['variant']) + found
    if row['key'] == 'form':
        return _no_box(ctx, ctx.variant)
    if row['section'] == 'questionnaires' and row['copy'] != rfp_rules.PAPER:
        return questionnaire_report.report(ctx.deal, row['form'])['problems']
    return []


def _no_box(ctx, variant):
    return [problem('no_box', text, fix={'tab': 'rfp'}) for text in form_fill.funding_warnings(ctx, variant)]


def _two_copies(wanted):
    ticked = [
        {'form': row['form_kind'], 'label': KIND_WORDS[row['form_kind']]} for row in wanted if row.get('form_kind')
    ]
    ticked += [
        {'form': PAPER_KIND[row['doc_kind']], 'label': KIND_WORDS[PAPER_KIND[row['doc_kind']]]}
        for row in wanted
        if row.get('doc_kind') in PAPER_KIND
    ]
    return [problem('two_copies', text) for text in rfp_rules.two_copies(ticked)]


def _many(ctx, wanted):
    out = []
    for row in wanted:
        out += [{**found, 'where': row['title']} for found in own(ctx, row)]
    return out + _two_copies(wanted) + deal.problems(ctx, counted=any(counted(row) for row in wanted))


def _size(draft):
    shown = draft['size'] * BASE64
    if shown <= MAIL_LIMIT:
        return []
    text = (
        f'The files on this email come to about {shown / 1_000_000:.0f} MB once attached — past the 20 MB most mail '
        'servers take. Send the largest separately or untick them.'
    )
    return [problem('too_large', text)]


def _report(key, label, found):
    return {'key': key, 'label': label, 'ok': not found, 'problems': found, 'ack': digest(found)}


def report(ctx, key, rows=None):
    rows = cards.rows(ctx) if rows is None else rows
    if key == PACKET:
        wanted = cards.in_packet(rows)
        found = _many(ctx, wanted) if wanted else [problem('nothing', 'Nothing is ticked for the packet.')]
        return _report(key, 'RFP packet', found)
    if key.startswith(DRAFT):
        draft = next((d for d in drafts.drafts(ctx, cards.in_packet(rows)) if d['key'] == key[len(DRAFT) :]), None)
        if draft is None:
            raise Unknown(key)
        by_key = {row['key']: row for row in rows}
        wanted = [by_key[name] for name in draft['attachment_keys']]
        return _report(key, f'{draft["name"]} email', _many(ctx, wanted) + _size(draft))
    row = next((found for found in rows if found['key'] == key), None)
    if row is None:
        raise Unknown(key)
    found = own(ctx, row)
    if row['section'] in ('census', 'census_forms') or row['key'] in COUNTED:
        found += deal.problems(ctx, counted=counted(row))
    return _report(key, row['title'], found)


def stale(ctx, key, ack, rows=None):
    if not ack:
        return None
    fresh = report(ctx, key, rows)
    return None if fresh['ack'] == ack else fresh


def pills(ctx, rows=None):
    rows = cards.rows(ctx) if rows is None else rows
    out = {}
    for row in rows:
        if not row['available']:
            continue  # nothing to check until it can be built (K41): the row says why instead
        found = own(ctx, row)
        if any(p['code'] == 'unsigned' for p in found):
            status = 'unsigned'
        else:
            status = 'problems' if found else 'ready'
        out[row['key']] = {'status': status, 'count': len(found)}
    return {'cards': out, 'deal': deal.problems(ctx)}
