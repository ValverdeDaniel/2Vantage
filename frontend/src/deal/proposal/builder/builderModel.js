/*
 * The proposal builder's small rules (plan.md §8.14; J18, J31, J47, J55, J61, J62; the old ProposalBuilder.jsx and
 * ProposalPlansCard.jsx at 891f1b3). Pure: which cards are on screen and open, the cards' one-line summaries, the row
 * and card-stat picks a click makes, and the line order. Every figure, word of a rule and count is the server's
 * (GET deals/{id}/proposal/); these only arrange them.
 */

export const ROWS_PREF_KEY = 'vantage.bnf.builder.pageRows'; // the old key: Key rows / All rows, per browser

const plural = (count, one, many = `${one}s`) => (count === 1 ? one : many);

/** A card's id for the open state: 'cover', or 'medical:quotes' for a line card. */
export const cardId = (card) => (card.line ? `${card.line}:${card.key}` : card.key);

/** A card's completed stamp ({by, at}) in the stored marks, or null. */
export function stampOf(stored, card) {
  const marks = card.line ? stored?.lines?.[card.line] : stored;
  return marks?.[card.key] ?? null;
}

/** The cards on screen: the deal's (when built) and the line tab's, from `/api/meta/` proposal. */
export function shownCards(proposalMeta, line) {
  const onScreen = new Set(proposalMeta?.on_screen ?? []);
  return (proposalMeta?.cards ?? [])
    .filter((card) => onScreen.has(card.key) && (!card.line || line))
    .map((card) => (card.line ? { key: card.key, line } : { key: card.key }));
}

/** Open unless completed, until this visit opens or shuts it (a completed card comes back collapsed). */
export function isOpen(openCards, stored, card) {
  const id = cardId(card);
  return id in openCards ? openCards[id] : !stampOf(stored, card);
}

/** "★ 3 on the proposal · 9 plans · 3 pages · 2 of 3 recommended" (the Plans card's summary). */
export function plansSummary(line) {
  const parts = [];
  if (line.starred) parts.push(`★ ${line.starred} on the proposal`);
  else parts.push(line.quotes ? 'Nothing picked: every quote goes on' : 'No quotes yet');
  if (line.pages) {
    const count = line.presented_ids.length;
    parts.push(`${count} ${plural(count, 'plan')} · ${line.pages} ${plural(line.pages, 'page')}`);
  }
  parts.push(recommendationWords(line).short);
  return parts.filter(Boolean).join(' · ');
}

/** The recommendation's status in words: {short, long, open} (J55; the old `bnf-pp-rec-status`). */
export function recommendationWords(line) {
  const rec = line.recommendation;
  const label = line.label;
  if (!rec.needs_pick && !rec.plans.length) return { short: '', long: `Nothing on ${label} to recommend yet.`, open: false };
  if (rec.sold.length) {
    return { short: 'Sold', long: `Sold: ${rec.sold.join(', ')}. The sold plan is the recommendation.`, open: false };
  }
  if (rec.groups.length) {
    const answered = rec.groups.filter((group) => group.answered).length;
    return {
      short: `${answered} of ${rec.groups.length} recommended`,
      long: `${answered} of ${rec.groups.length} current plans have a recommendation.`,
      tail: 'Each current plan needs a pick, a replacement or “keep”, before the proposal can go to the client.',
      open: answered < rec.groups.length,
    };
  }
  if (rec.plans.length) {
    const keep = rec.plans.length === 1 && rec.plans[0].keep ? 'keeping ' : '';
    return {
      short: `Recommended: ${rec.plans.map((plan) => plan.words).join(', ')}`,
      long: `We recommend ${keep}${rec.plans.map((plan) => plan.words).join(' and ')}.`,
      open: !rec.covered,
    };
  }
  return {
    short: 'No recommendation yet',
    long: 'Pick Recommend under one plan above: the proposal cannot go to the client without one.',
    open: true,
  };
}

/** "Every row with a value" or "4 of 31 rows" (the rows card's summary). */
export function rowsSummary(spec, total) {
  return spec.rows == null ? 'Every row with a value' : `${spec.rows.length} of ${total} rows`;
}

/** The rows a tick leaves picked, in the line's order (`null` = every row with a value, the default). */
export function toggledRows(picked, keys, key) {
  const base = new Set(picked ?? keys);
  if (base.has(key)) base.delete(key);
  else base.add(key);
  return keys.filter((k) => base.has(k));
}

/** A whole group on or off. */
export function groupRows(picked, keys, groupKeys, on) {
  const base = new Set(picked ?? keys);
  for (const key of groupKeys) {
    if (on) base.add(key);
    else base.delete(key);
  }
  return keys.filter((k) => base.has(k));
}

/** The row picker's groups, in the line's order: [{group, label, rows}]. */
export function rowSections(rows) {
  const out = [];
  for (const row of rows) {
    if (!out.length || out.at(-1).group !== row.group) out.push({ group: row.group, label: row.group_label, rows: [] });
    out.at(-1).rows.push(row);
  }
  return out;
}

/** The list with item `i` moved one place (`dir` −1 or 1), or null at an end. */
export function moved(list, i, dir) {
  const j = i + dir;
  if (j < 0 || j >= list.length) return null;
  const next = [...list];
  [next[i], next[j]] = [next[j], next[i]];
  return next;
}

/** The builder's line order after ◀ / ▶ on `key`, or null at an end (J31). */
export function lineOrder(lines, key, dir) {
  const keys = lines.map((line) => line.line);
  return moved(keys, keys.indexOf(key), dir);
}

/** The line to show: the wanted one when the builder has it, else its first. */
export function chooseLine(lines, wanted) {
  return lines.some((line) => line.line === wanted) ? wanted : (lines[0]?.line ?? '');
}

export function readRowsPref(storage) {
  try {
    return storage?.getItem(ROWS_PREF_KEY) === 'all' ? 'all' : 'key';
  } catch {
    return 'key';
  }
}

export function writeRowsPref(storage, value) {
  try {
    storage?.setItem(ROWS_PREF_KEY, value === 'all' ? 'all' : 'key');
  } catch {
    /* private mode: the choice lasts until the page is left */
  }
}
