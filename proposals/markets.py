"""Markets checked: who we asked, who quoted, and what the client sees (plan.md §8.14; J63, K117). Pure.

Stephanie, 2026-09-29: "I do normally put in a marketing summary slide that basically just says here's all the
carriers we went to. Did they quote or not?" Per line, Carrier | Quoted | On this proposal | Note, the incumbent as
"Carrier (Current)" with Quoted "–". Ported from old Vantage 891f1b3 `pipeline/markets.py`, rules unchanged:

- asked: who the sent drafts named for the line (`rfp.asked_by_line`, the frozen send record); editing the picks later
  changes nothing here. Until a send is recorded only the carriers that quoted are listed ("no RFP sent").
- quoted: a non-current plan on the line, its carrier matched through `deals.carriers.identity` (one row per carrier;
  "Unknown carrier" belongs to nobody); presented: any of its plans is on the proposal (`quotes.presented`).
- the incumbent is its own row, first, and never "No"; then the carriers that quoted in the order the proposal shows
  their plans; then the ones asked who did not.
- a line appears only once something marketed it: a carrier asked for it, or a quote back on it.
- an unregistered asked carrier ("VSP") merges with the one quote or incumbent whose name starts the same way ("VSP
  Vision Care Inc."); a free-text carrier that quoted nowhere shows once, on the first line it was asked for.
`config.markets` holds the producer's choices: `on` (true, false, or null for automatic: shown once a send is
recorded and a quote is back) and per line the notes ({carrier id: text}) and the hidden carriers.
"""

from deals import carriers

FREE = 'n:'  # the identity prefix of a name the carrier registry does not know


def _same_carrier(asked_name, other_name):
    """Two spellings of one unregistered carrier share a leading run of words once corporate words are off."""
    a, b = carriers.norm(asked_name).split(), carriers.norm(other_name).split()
    if not a or not b:
        return False
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return longer[: len(shorter)] == shorter


def _line_carriers(line):
    """(current, quoted, raw, unknown, rank): the incumbent and the quoting carriers by identity (display names), the
    names as typed, the quotes no carrier claims, and each quoting carrier's place in the proposal's order."""
    current, quoted, raw, unknown, rank = {}, {}, {}, [], {}
    for plan in line['plans']:
        identity = carriers.identity(plan['carrier'])
        if plan['current']:
            if identity:
                current.setdefault(identity, carriers.display_name(plan['carrier']))
                raw.setdefault(identity, plan['carrier'])
            continue
        if not identity:
            unknown.append(f'{str(plan["carrier"] or "").strip() or "Unknown carrier"} ({plan["name"] or "plan"})')
            continue
        quoted.setdefault(identity, carriers.display_name(plan['carrier']))
        raw.setdefault(identity, plan['carrier'])
        rank.setdefault(identity, len(rank))
    incumbent = line.get('incumbent') or ''
    if not current and carriers.identity(incumbent):
        identity = carriers.identity(incumbent)
        current[identity] = carriers.display_name(incumbent)
        raw.setdefault(identity, incumbent)
    return current, quoted, raw, unknown, rank


def _merged_into(found, identity, name):
    """The quote or incumbent identity an unregistered asked carrier is on this line, or None (none, or several)."""
    if not identity.startswith(FREE):
        return None
    current, quoted, raw = found[0], found[1], found[2]
    candidates = [i for i in [*current, *quoted] if i.startswith(FREE) and _same_carrier(name, raw.get(i, ''))]
    return candidates[0] if len(candidates) == 1 else None


def _free_text(lines, asked, per_line):
    """(free-text carriers that quoted somewhere, {identity: the first line it was asked for})."""
    quoted_somewhere, first = set(), {}
    for line in lines:
        key = line['key']
        for entry in asked.get(key, []):
            identity = entry['id']
            if not identity.startswith(FREE):
                continue
            first.setdefault(identity, key)
            if _merged_into(per_line[key], identity, entry['name']) or identity in per_line[key][1]:
                quoted_somewhere.add(identity)
    return quoted_somewhere, first


def _asked_here(line, asked, found, free):
    quoted_somewhere, first = free
    here, ids = [], set()
    for entry in asked.get(line['key'], []):
        identity, name = entry['id'], entry['name']
        target = _merged_into(found, identity, name)
        if target:
            ids.add(target)
            continue
        if identity.startswith(FREE) and identity not in found[1]:
            if identity in quoted_somewhere or first.get(identity) != line['key']:
                continue
        here.append((identity, name))
        ids.add(identity)
    return here, ids


def _rows(line, found, here, ids, settings):
    current, quoted, raw, unknown, rank = found
    notes, hidden = settings
    shown = {carriers.identity(plan['carrier']) for plan in line['plans'] if plan['shown']}

    def row(identity, name, is_current, quoted_flag):
        default = line.get('renewal_note', '') if is_current else ''
        note = str(notes.get(identity) or '').strip()
        return {
            'id': identity,
            'carrier': name,
            'current': is_current,
            'asked': identity in ids,
            'quoted': quoted_flag,
            'presented': identity in shown,
            'note': note or default,
            'note_default': default,
            'hidden': identity in hidden,
        }

    rows = [row(i, n, True, None) for i, n in current.items()]
    rows += [row(i, quoted[i], False, True) for i in sorted((i for i in quoted if i not in current), key=rank.get)]
    rows += [row(i, n, False, False) for i, n in here if i not in current and i not in quoted]
    unmatched = []
    if any(r['quoted'] is False for r in rows):
        unmatched = sorted({raw[i] for i in [*quoted, *current] if i.startswith(FREE) and i not in ids} | set(unknown))
    return rows, unmatched


def marketing(lines, asked, settings):
    """The producer's view.

    `lines`: the proposal's lines in order, each {key, label, plans: [{carrier, name, current, shown}] in the
    proposal's order, incumbent: the coverage row's carrier ('' when none), renewal_note}; `asked`:
    `rfp.asked_by_line`; `settings`: {on, lines: {line: (notes, hidden)}}.
    → {has_asks, auto, override, on, lines: [{key, label, rows: [{id, carrier, current, asked, quoted, presented,
    note, note_default, hidden}], unmatched: [names to check]}]}; `quoted` is True, False (asked, nothing back) or
    None (the incumbent)."""
    per_line = {line['key']: _line_carriers(line) for line in lines}
    free = _free_text(lines, asked, per_line)
    out, any_quote = [], False
    for line in lines:
        found = per_line[line['key']]
        here, ids = _asked_here(line, asked, found, free)
        if not (here or set(found[1]) - set(found[0])):
            continue
        rows, unmatched = _rows(line, found, here, ids, settings['lines'].get(line['key'], ({}, set())))
        any_quote = any_quote or bool(set(found[1]) - set(found[0]))
        out.append({'key': line['key'], 'label': line['label'], 'rows': rows, 'unmatched': unmatched})
    has_asks = bool(asked)
    auto = has_asks and any_quote
    override = settings['on'] if isinstance(settings['on'], bool) else None
    return {
        'has_asks': has_asks,
        'auto': auto,
        'override': override,
        'on': override if override is not None else auto,
        'lines': out,
    }


def line_rows(facts, line):
    """One line's rows when a send is recorded, else None: what the "Who we went to" figure reads."""
    if not facts['has_asks']:
        return None
    return next((entry for entry in facts['lines'] if entry['key'] == line), None)
