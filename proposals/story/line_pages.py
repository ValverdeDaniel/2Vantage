"""One line's pages in "Your coverage" (plan.md §9.5; J131, J132, J134, J135; old Vantage 891f1b3
`proposal_presentation._line_pages`, `_renewal_set_pages` and `proposal_pdf._option_index`, `_package_summary`,
`_cost_flags`, `_cost_table`). Pure.

In order: the renewal set (each current plan beside its renewal, at most three pairs a slide and never split, the
totals on the last; the carrier's first offer first when the renewal was negotiated); "Your options" when the line
runs over several pages; one plan set a page (`exhibit.page`); a cost-only page when the comparison part is off; what
employees pay (only when a plan other than today's has an employee cost); then the recommendation (`recommend`). The
pages are the one splitter's (`pages.sequence`, laid out as Pages shows them), so the screen and the files cannot part.
"""

from ..layout import fit, tokens
from ..layout import table as tb
from . import exhibit, look, recommend

TIER_WORDS = {'EE': 'Employee only', 'ES': 'Employee + spouse', 'EC': 'Employee + child(ren)', 'FAM': 'Family'}


def caption(page):
    words = page['caption'] or page['carrier']
    return f'{words} (continued)' if words and page['continued'] else words


def _plans(line, ids):
    return [line['plans'][pid] for pid in ids if pid in line['plans']]


def renewal_pages(line, pages, colours, with_cost):
    chunks = [_plans(line, page['plan_ids']) for page in pages if page['part'] == 'renewal']
    if not chunks:
        return []
    offers_ = [p for chunk in chunks for p in chunk if not p['current']]
    negotiated = any(p['first'] for p in offers_)
    label = line['label']
    heading = f'{label} — {"negotiated renewal" if negotiated else "renewal"}'
    out = []
    if negotiated:
        first = {p['id']: p['first'] for p in offers_ if p['first']}
        totals = exhibit.set_totals(offers_, line, first) if with_cost else None
        for number, chunk in enumerate(chunks):
            out.append(
                exhibit.page(
                    f'{label} — the first renewal offer',
                    line,
                    chunk,
                    colours,
                    offers=first,
                    with_cost=with_cost,
                    plain=True,
                    totals=totals if number == len(chunks) - 1 else None,
                )
            )
    totals = exhibit.set_totals(offers_, line) if with_cost else None
    picks = set(line['picks'])
    for number, chunk in enumerate(chunks):
        mine = [p['id'] for p in chunk if not p['current']]
        speak = None
        if len(mine) > 1 and all(pid in picks for pid in mine):
            speak = f'We recommend the {"negotiated " if negotiated else ""}renewal on all {len(mine)} plans.'
        out.append(
            exhibit.page(
                heading,
                line,
                chunk,
                colours,
                picks=picks,
                with_cost=with_cost,
                plain=True,
                speak=speak,
                totals=totals if number == len(chunks) - 1 else None,
            )
        )
    return out


def fitted(build):
    """A page of tables at the largest type (12 down to the 8 pt floor) at which they all share one page; at the floor
    it runs on, "(continued)". `build(size)` gives the page's flowables, its title first."""
    for size in fit.sizes(look.CELL):
        found = build(size)
        if fit.height_under(found[1:]) <= tokens.BODY_H:
            return found
    return build(tokens.TABLE_TYPE['floor'])


def option_index(line, colours, title):
    """Every option on a long line, on one page: where a reader finds their way when the comparison runs on."""
    options = [line['plans'][pid] for pid in line['order'] if not line['plans'][pid]['current']]

    def build(size):
        rows = [look.heads(['Option', 'Carrier', 'Plan', 'Monthly', '% change'], colours, size, center_from=3)]
        for plan in options:
            option = f'Option {plan["option"]}' if plan['option'] else ''
            pct = look.pct((plan['change'] or {}).get('pct')) if plan['change'] else '—'
            texts = [option, plan['carrier'], plan['name'], look.money(plan['monthly']), pct]
            rows.append(look.row(texts, colours, size, center_from=3, bold_first=False))
        return [look.title(title), look.grid(rows, look.shares([0.12, 0.26, 0.38, 0.12, 0.12]), colours)]

    return fitted(build)


def _summary_table(current, options, colours, size):
    rows = [look.heads(['Option', 'Plan', 'Monthly', 'Annual', 'Change', '% change'], colours, size, center_from=2)]
    figures = [look.money(current['monthly']), look.money(current['annual']), '—', '—']
    texts = ['Current', f'{current["carrier"]} — {current["name"]}', *figures]
    rows.append(look.row(texts, colours, size, center_from=2))
    rows[-1]['fill'] = colours['current']
    for plan in options:
        change = plan['change'] or {}
        label = f'Option {plan["option"]}' if plan['option'] else plan['priced_label'] or 'Option'
        figures = [look.money(plan['monthly']), look.money(plan['annual'])]
        figures += [look.signed(change.get('delta')), look.pct(change.get('pct'))]
        texts = [label, f'{plan["carrier"]} — {plan["name"]}', *figures]
        rows.append(look.row(texts, colours, size, center_from=2, bold_first=False))
    widths = [1.5 * 72, 4.4 * 72] + [(tokens.BODY_W - 5.9 * 72) / 4] * 4
    return look.grid(rows, widths, colours)


def package_summary(line, colours, title, shown):
    """Every option the pages show against what it replaces (J39; old `_package_summaries`): monthly, annual, the
    change in dollars and percent; one table, or one per current plan on a line with several, each under the words
    its comparison pages carry, all at one type size that lets them share the page. [] when no option has a price
    (why is the builder's to say)."""
    plans = line['plans']
    currents = [plans[pid] for pid in line['order'] if plans[pid]['current']]
    options = [plans[pid] for pid in line['order'] if pid in shown and not plans[pid]['current']]
    if not currents or not any(p['monthly'] is not None for p in options):
        return []
    groups = (
        [(currents[0], options)]
        if len(currents) == 1
        else [(current, [p for p in options if current['id'] in p['bases']]) for current in currents]
    )
    groups = [(current, mine) for current, mine in groups if mine]
    if not groups:
        return []

    def build(size):
        out = [look.title(title)]
        for current, mine in groups:
            if len(currents) > 1:
                words = f'Replacing: {current["carrier"]} {current["name"]}'
                out.append(look.para(words, 'caption', colours, space_before=10))
            out.append(_summary_table(current, mine, colours, size))
        return out

    return fitted(build)


def cost_flags(plans):
    return {
        'monthly': any(p['monthly'] is not None for p in plans),
        'annual': any(p['annual'] is not None for p in plans),
        'pct': any(p['change'] and p['change']['pct'] is not None for p in plans),
        'credit': any((p['credit'] or {}).get('annual') for p in plans),
        'employee': any(p['employee'] for p in plans),
    }


def cost_table(page_plans, flags, colours, picks):
    """The cost rows alone: the premium, the year, the change, a credit and its net, what employees pay per tier."""
    size, ink, soft = look.CELL, colours['ink'], colours['ink2']
    rows = [{'kind': 'head', 'cells': [tb.cell('Cost', size, '#ffffff', True)]}]
    rows[0]['cells'] += [tb.rich(exhibit.heading_runs(p, size, colours, p['id'] in picks), 'c') for p in page_plans]

    def add(label, texts, bold=False):
        cells = [tb.cell(label, size, soft, bold)] + [tb.cell(text, size, ink, align='c') for text in texts]
        rows.append({'kind': 'plain', 'cells': cells})

    if flags['monthly']:
        add('Est. group monthly premium', [look.money(p['monthly']) for p in page_plans], True)
    if flags['annual']:
        add('Est. group annual premium', [look.money(p['annual']) for p in page_plans])
    if flags['pct']:
        add('% from current', [look.pct((p['change'] or {}).get('pct')) for p in page_plans])
    if flags['credit']:
        credits = [(p['credit'] or {}) for p in page_plans]
        add('First-year premium credit', [f'− {look.money(c["annual"])}' if c.get('annual') else '—' for c in credits])
        add(
            'Net annual premium (after credit)',
            [look.money(c.get('net_annual', p['annual'])) for c, p in zip(credits, page_plans, strict=True)],
        )
    if flags['employee']:
        for tier, words in TIER_WORDS.items():
            texts = [look.formatting.rate((p['employee'] or {}).get(tier)) or '—' for p in page_plans]
            add(f'Employee cost / mo — {words}', texts)
    count = len(page_plans)
    width = min(tokens.MAX_COL, (tokens.BODY_W - tokens.LABEL_W) / max(1, count))
    current = [n + 1 for n, p in enumerate(page_plans) if p['current']]
    picked = [n + 1 for n, p in enumerate(page_plans) if p['id'] in picks]
    return look.grid(rows, [tokens.LABEL_W] + [width] * count, colours, current=current, picked=picked)


def pages(line, facts, colours):
    """The line's pages, each a list of flowables, in print order."""
    label = line['label']
    parts = line['parts']
    comparison, cost = parts['comparison'], parts['cost']
    picks = set(line['picks'])
    options = [page for page in line['pages'] if page['part'] == 'options']
    out = []
    if comparison:
        out += renewal_pages(line, line['pages'], colours, cost)
    if len(options) > 1 and comparison:
        shown = {pid for page in options for pid in page['plan_ids']}
        summary = (
            package_summary(line, colours, f'{label} — your options', shown)
            if facts['package_summary'] and cost
            else []
        )
        out.append(summary or option_index(line, colours, f'{label} — your options'))
    if comparison:
        for page in options:
            plans = _plans(line, page['plan_ids'])
            words = caption(page)
            names = [p['name'] for p in plans if p['id'] in picks and not p['current']]
            speak = f'We recommend {" and ".join(names)}.' if names else None
            title = f'{label} — {words}' if words else f'{label} — plan comparison'
            out.append(exhibit.page(title, line, plans, colours, picks=picks, with_cost=cost, speak=speak))
    elif cost:
        flags = dict(cost_flags(line['plans'].values()), employee=False)
        for page in options:
            plans = _plans(line, page['plan_ids'])
            if any(p['monthly'] is not None for p in plans):
                out.append(
                    [look.title(f'{label} — {caption(page) or "cost"}'), cost_table(plans, flags, colours, picks)]
                )
    if cost:
        priced = [line['plans'][pid] for pid in line['order'] if line['plans'][pid]['employee']]
        if any(not p['current'] for p in priced):
            flags = {'monthly': False, 'annual': False, 'pct': False, 'credit': False, 'employee': True}
            for start in range(0, len(priced), tokens.COLUMNS):
                chunk = priced[start : start + tokens.COLUMNS]
                out.append([look.title(f'{label} — what employees pay'), cost_table(chunk, flags, colours, picks)])
    if parts['recommendation']:
        out += recommend.pages(line, colours)
    return [page for page in out if page]
