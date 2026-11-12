"""The one page splitter (plan.md §5.4, §9.5; J.6.3; F37, F38, J49; D-221). Pure.

A line's comparison pages as the client documents print them, page by page, plans as columns left to right: the
Advisor's ▦ Pages ("What the client will see", slice 14) draws them now, and the PowerPoint and PDF (slices 29, 31)
lay out these same pages, so the screen and the deck cannot part (ported from old Vantage at 7385bb3,
`presentation_model.chunk`, `line_pages`, `_pages_by_current`, `renewal_set`, `pair_slides`, `deck_sequence`).

- Six plans a slide (`PER_PAGE`, D-221). A current plan shown again on a later page counts as one of the six.
- By carrier (the default layout): the leading plans (the current plans and their priced versions) open page one
  with the first carrier's first run; every later run starts a page of its own beside the current plans, which
  repeat. A carrier that runs over a page continues on the next ("continued").
- By current plan: on a line with two or more current plans, once any option is linked to one (`group`), each current
  plan gets its own pages with its priced versions and the options compared with it ("Replacing: …"); then the
  current plans nothing replaces, together; then the options linked to nothing ("Other options").
- Side by side runs every option after the leading plans as one group; best only is the current plans beside the
  picks alone (falling back to by carrier when no pick is shown).
- The renewal page (the Presentation format): on a line with two or more current plans where each has its renewal
  (or a priced version of it) on the proposal, those pairs take a page of their own, at most three pairs a slide and
  never split (`pair_slides`), and what that page answers for prints on no other.

Columns are `Column`s in the line's order (`quotes.order.layout`, filtered to what the line presents): nothing here
orders or picks plans. `sequence` returns the pages; `reading_order` the order the client first meets the plans in,
which predicts and later stamps the option numbers (§5.4, J159; J.5 B4).
"""

from collections import namedtuple

PER_PAGE = 6  # plans a slide holds (D-221: "cap it at 6 plans per page")
LAYOUTS = ('by_carrier', 'side_by_side', 'best_only')
DEFAULT_LAYOUT = 'by_carrier'
NO_OPTIONS = 'Current plans with no options shown'
OTHER_OPTIONS = 'Other options'

# One plan on the pages: `current` and `lead` (a current plan, or a priced version of one); `carrier` groups the runs
# (`deals.carriers.identity`, else "plan:<id>") and `carrier_name` names them; `group` is the current plan an option is
# compared with (its renewal's plan or its first link) or None; `renews` the current plan its quote renews or None;
# `version` says it is a priced version (it rides behind its plan).
Column = namedtuple('Column', 'id current lead carrier carrier_name group renews version')


def split(lead, titles, groups, per_page):
    """The page rule on plan counts (old `chunk`). `lead` plans open page one with the first group's first run; every
    later run starts a page of its own beside the `titles` plans, which repeat. A run takes at most `per_page` less
    what the page already holds, and at least one plan, so a lead wider than a page is never split.
    Returns (first, later): runs as (group index, start within the group, count)."""
    lead, titles, per_page = max(0, int(lead)), max(0, int(titles)), max(1, int(per_page))
    first, later = [], []
    for index, size in enumerate(groups):
        remaining, start = int(size), 0
        while remaining > 0:
            if index == 0 and start == 0:
                take = min(max(1, per_page - lead), remaining)
                first.append((index, start, take))
            else:
                take = min(max(1, per_page - titles), remaining)
                later.append((index, start, take))
            start += take
            remaining -= take
    return first, later


def _page(plan_ids, *, repeat_ids=(), carrier='', continued=False, caption='', part='options'):
    return {
        'part': part,
        'plan_ids': list(plan_ids),
        'repeat_ids': list(repeat_ids),
        'caption': caption,
        'carrier': carrier or '',
        'continued': bool(continued),
    }


def leading(columns):
    """The ids of the prefix made of the current plans and their priced versions."""
    lead = []
    for column in columns:
        if not column.lead:
            break
        lead.append(column.id)
    return lead


def carrier_runs(columns):
    """The columns as consecutive runs of one carrier: [(carrier name, [ids])]; a carrier that comes back after
    another starts a new run."""
    runs = []
    for column in columns:
        if runs and runs[-1][0] == column.carrier:
            runs[-1][2].append(column.id)
        else:
            runs.append((column.carrier, column.carrier_name, [column.id]))
    return [(name, ids) for _key, name, ids in runs]


def _flow(lead, current, runs, per_page):
    """Page one (the lead and the first run), then a page per later run beside the repeated current plans."""
    first, later = split(len(lead), len(current), [len(ids) for _name, ids in runs], per_page)
    page_one = _page(lead)
    for index, start, take in first:
        page_one['plan_ids'] += runs[index][1][start : start + take]
        page_one['carrier'] = runs[index][0] or ''
    pages = [page_one]
    for index, start, take in later:
        name, ids = runs[index]
        pages.append(_page(current + ids[start : start + take], repeat_ids=current, carrier=name, continued=start > 0))
    return pages


def by_current(columns, captions, per_page=PER_PAGE):
    """Pages by what each option replaces (D-174): each current plan with its priced versions and the options linked
    to it, so the columns the other current plans took go to its options; then the current plans nothing replaces;
    then the options linked to nothing. `captions` names each current plan's pages ("Replacing: Aetna HMO 1000")."""
    current = [c.id for c in columns if c.current]
    pages, alone = [], []
    for cur in current:
        lead = [cur] + [c.id for c in columns if not c.current and c.lead and c.group == cur]
        options = [c.id for c in columns if not c.lead and c.group == cur]
        caption = captions.get(cur, '')
        if not options:
            if len(lead) == 1:
                alone.append(cur)
            else:
                pages.append(_page(lead, caption=caption))
            continue
        first, later = split(len(lead), 1, [len(options)], per_page)
        for _index, start, take in first:
            pages.append(_page(lead + options[start : start + take], caption=caption))
        for _index, start, take in later:
            pages.append(
                _page([cur] + options[start : start + take], repeat_ids=[cur], caption=caption, continued=True)
            )
    for start in range(0, len(alone), per_page):
        pages.append(_page(alone[start : start + per_page], caption=NO_OPTIONS, continued=start > 0))
    others = [c.id for c in columns if not c.current and c.group is None and not c.lead]
    for start in range(0, len(others), per_page):
        pages.append(_page(others[start : start + per_page], caption=OTHER_OPTIONS, continued=start > 0))
    return pages


def line_pages(columns, per_page=PER_PAGE, layout=DEFAULT_LAYOUT, picks=(), captions=None):
    """One line's pages under the column cap: [{part, plan_ids, repeat_ids, caption, carrier, continued}]. A line with
    no current plan repeats nothing; one with several repeats them all until an option is linked to one, then it goes
    by current plan. No plans, no pages."""
    if not columns:
        return []
    current = [c.id for c in columns if c.current]
    shown = {c.id for c in columns}
    chosen = [pid for pid in picks if pid in shown and pid not in current]
    if layout == 'best_only' and chosen:
        runs = [('', chosen)]
        return _flow(current, current, runs, per_page)
    lead = leading(columns)
    if len(current) >= 2 and any(c.group is not None for c in columns if not c.lead):
        return by_current(columns, captions or {}, per_page)
    rest = [c for c in columns if c.id not in set(lead)]
    if layout == 'side_by_side':
        runs = [('', [c.id for c in rest])] if rest else []
    else:
        runs = carrier_runs(rest)
    return _flow(lead, current, runs, per_page)


def renewal_set(columns):
    """A line's renewal page, or None: one offer for each of two or more current plans, the carrier's renewal or a
    priced version of it (preferred, as the negotiated figure). Every current plan needs its offer, or the page would
    look complete and not be. → {pairs: [[current, offer]], shown: {every plan the page answers for}}."""
    current = [c.id for c in columns if c.current]
    if len(current) < 2:
        return None
    pairs, shown = [], set()
    for cur in current:
        offers = [c for c in columns if not c.current and c.renews == cur]
        if not offers:
            return None
        priced = [c for c in offers if c.version]
        pairs.append([cur, (priced or offers)[0].id])
        shown.update(c.id for c in offers)
    return {'pairs': pairs, 'shown': shown}


def pair_slides(pairs, per_page=PER_PAGE):
    """A renewal page's pairs over slides: never split, at most `per_page // 2` a slide, shared evenly (five pairs
    print three and two, four print two and two, seven three, two and two)."""
    pairs = list(pairs or [])
    if not pairs:
        return []
    per = max(1, int(per_page) // 2)
    count = -(-len(pairs) // per)
    size, extra = divmod(len(pairs), count)
    chunks, start = [], 0
    for number in range(count):
        take = size + (1 if number < extra else 0)
        chunks.append(pairs[start : start + take])
        start += take
    return chunks


def _current_of(page, columns):
    """The current plan an options page's plans replace (for "＋ Add a plan" beside it): the plan a page by current
    plan opens on; None on the pages of no one plan."""
    ids = page['plan_ids']
    if not ids or not page['caption'] or page['caption'] in (NO_OPTIONS, OTHER_OPTIONS):
        return None
    return ids[0] if columns[ids[0]].current else None


def sequence(columns, captions=None, per_page=PER_PAGE, layout=DEFAULT_LAYOUT, presentation=True, picks=()):
    """The line's pages as the deck prints them: the renewal slides first (the Presentation format), then the options
    pages. Each page: {part: 'renewal' | 'options', plan_ids, repeat_ids, caption, carrier, continued, current_id}."""
    by_id = {c.id: c for c in columns}
    offers = renewal_set(columns) if presentation else None
    rest = [c for c in columns if not offers or c.id not in offers['shown']]
    pages = line_pages(rest, per_page, layout, picks, captions)
    if offers:  # the current plans the renewal page already shows need no page alone
        pages = [page for page in pages if any(not by_id[pid].current for pid in page['plan_ids'])]
    slides = []
    if offers:
        for number, chunk in enumerate(pair_slides(offers['pairs'], per_page)):
            ids = [pid for pair in chunk for pid in pair]
            slides.append({**_page(ids, part='renewal', continued=number > 0), 'current_id': None})
    for page in pages:
        slides.append({**page, 'current_id': _current_of(page, by_id)})
    return slides


def reading_order(pages):
    """Every plan the pages show, in the order the client first meets it."""
    seen, order = set(), []
    for page in pages:
        for pid in page['plan_ids']:
            if pid not in seen:
                seen.add(pid)
                order.append(pid)
    return order


def first_pages(pages):
    """{plan id: the page number (from 1) it first shows on}."""
    out = {}
    for number, page in enumerate(pages, start=1):
        for pid in page['plan_ids']:
            out.setdefault(pid, number)
    return out
