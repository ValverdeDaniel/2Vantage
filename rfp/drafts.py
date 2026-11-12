"""The emails that carry the request (plan.md §9.11; K57–K61, K63–K66, K104, K120). Pure over one request and its
packet rows. Written for a person to send from their own mailbox, never sent by the app (OQ67, OQ82).

- **Through Warner:** one draft to Warner's quoting inbox, carrying the whole packet and the request in words.
- **Direct:** one draft per picked carrier, plus one for "Other carriers" when that box is filled. To is blank (the rep
  fills it in; OQ59); the subject lists only the lines that carrier quotes (K60, bug 20); each carries the cover, the
  shared documents and that carrier's own files (`audience.receives`), and never names another carrier.
- CC and "Please reply all": the returns inbox (OQ65). The body follows §9.11; empty lines are left out.
- `sent`: what a send stored (K64: date, who), shown "Nov 11" (K65); `sent_earlier`: sends whose draft no longer
  exists because the route or the picks changed (K120: they still count as asked, and Undo takes them back).
"""

from . import audience, carriers, words

WARNER, OTHER = audience.WARNER, audience.OTHER
WARNER_LABEL, OTHER_LABEL = 'Warner Pacific', 'Other carriers'


def subject(prefix, ctx, keys):
    effective = words.short_date(ctx.deal.effective_date)
    parts = [f'eff. {effective}' if effective else '', ', '.join(words.short_lines(keys))]
    return f'{prefix}: {ctx.group_name}' + ''.join(f' | {part}' for part in parts if part)


def sign_off(ctx):
    found = ['Thank you,', ctx.agent, ctx.agency.name or '', ctx.agency.phone or '']
    return [line for line in found if line]


def body(ctx, opening, docs_line, attached, extra):
    effective = words.long_date(ctx.deal.effective_date)
    lines = ['Hi,', '']
    head = f'{opening}{f", effective {effective}" if effective else ""}.'
    if attached:
        lines += [f'{head} {docs_line}', *[f'- {row["title"]}' for row in attached]]
    else:
        lines.append(head)
    lines.append('')
    if extra:
        lines += [extra, '']
    due = words.long_date(ctx.stored['due_date'])
    if due:
        lines += [f'Quotes are due back by {due}.', '']
    if ctx.return_to:
        lines += [f'Please reply all so your quote reaches {ctx.return_to}.', '']
    return '\n'.join(lines + sign_off(ctx))


def _draft(ctx, key, label, to, subject_line, opening, docs_line, attached, extra):
    return {
        'key': key,
        'label': label,
        'name': label if key != OTHER else OTHER_LABEL,
        'to': to,
        'cc': ctx.return_to,
        'subject': subject_line,
        'body': body(ctx, opening, docs_line, attached, extra),
        'attachment_keys': [row['key'] for row in attached],
        'attachments': [row['title'] for row in attached],
        'size': sum(row.get('size') or 0 for row in attached),
    }


def drafts(ctx, packed):
    """[draft] for the route, from the rows in the packet (`cards.packet.in_packet`)."""
    group = ctx.group_name
    if ctx.route != 'direct':
        return [
            _draft(
                ctx,
                WARNER,
                WARNER_LABEL,
                carriers.WARNER_QUOTING_EMAIL,
                subject('Quote request', ctx, ctx.lines),
                f'Please see the attached quote request for {group}',
                'The documents to quote are attached:',
                packed,
                words.request_summary(ctx),
            )
        ]
    opening, docs_line = f'Please see the attached RFP for {group}', 'The documents to quote are also attached:'
    notes = ctx.stored['notes']
    out = []
    for key in ctx.picked:
        attached = [row for row in packed if audience.receives(row, key, ctx)]
        line = subject('RFP', ctx, audience.quoting_lines(ctx, key))
        out.append(_draft(ctx, key, ctx.chip[key]['name'], '', line, opening, docs_line, attached, notes))
    if ctx.other_text():
        attached = [row for row in packed if audience.receives(row, None, ctx)]
        label = f'{OTHER_LABEL} ({ctx.other_text()})'
        out.append(_draft(ctx, OTHER, label, '', subject('RFP', ctx, ctx.lines), opening, docs_line, attached, notes))
    return out


def short_on(on):
    """'2026-11-11' → 'Nov 11' (K65)."""
    found = words.as_date(on)
    return f'{found:%b} {found.day}' if found else ''


def label_of(key):
    """What a stored send is called once its draft is gone (K120)."""
    if key == WARNER:
        return WARNER_LABEL
    if key == OTHER:
        return OTHER_LABEL
    return words.carrier_name(key)


def sent_block(send, names):
    if not isinstance(send, dict):
        return None
    return {'on': send.get('on') or '', 'shown': short_on(send.get('on')), 'by': names.get(send.get('by'), '')}


def block(ctx, packed, sends, names, changed=None):
    """The Emails card: the drafts with their sends, how many are marked sent, and the sends whose draft is gone."""
    found = drafts(ctx, packed)
    keys = {draft['key'] for draft in found}
    for draft in found:
        draft['sent'] = sent_block((sends or {}).get(draft['key']), names)
        draft['changed'] = (changed or {}).get(draft['key'], [])
    earlier = [
        {'key': key, 'label': label_of(key), **sent_block(send, names)}
        for key, send in sorted((sends or {}).items(), key=lambda item: (str((item[1] or {}).get('on')), item[0]))
        if key not in keys and isinstance(send, dict)
    ]
    return {
        'route': ctx.route,
        'rows': found,
        'sent_count': sum(1 for draft in found if draft['sent']),
        'total': len(found),
        'sent_earlier': earlier,
        'any_sent': bool(sends),
    }
