// The counts card's pure rules (plan.md §5.5, §8.14; F85, F88, F91, F92): which plans it offers, the rows it starts
// from, what is wrong with a row, the body it saves and the words around it. Keys and labels come from /api/meta/
// `enrollment` and the comparison's `enrollment` block; every figure is the server's.

const MORE = 3;

/** A priced version prices its plan's people, so the card never offers it (the old PlanCountsCard). */
export function isVersion(plan) {
  return Boolean(plan.derived_from) && plan.derived?.kind !== 'duplicate';
}

export function candidates(plans) {
  return plans.filter((plan) => !isVersion(plan));
}

function hasCounts(figures) {
  return Object.values(figures ?? {}).some((value) => Number(value) > 0);
}

/** The plans the card starts with: those with their own counts, else the ones asked for (the split, plans bought
 *  together). */
export function initialPicked(plans, preselect) {
  const typed = plans.filter((plan) => hasCounts(plan.enrollment)).map((plan) => plan.id);
  return [...new Set([...typed, ...(preselect ?? [])])];
}

export function blankRow(keys, figures) {
  return Object.fromEntries(keys.map((key) => [key, figures?.[key] ? String(figures[key]) : '']));
}

export function initialRows(plans, keys) {
  return Object.fromEntries(plans.map((plan) => [plan.id, blankRow(keys, plan.enrollment)]));
}

/** The keys whose text is not a count: whole people only; a volume may carry cents. */
export function badKeys(row, keys) {
  return keys.filter((key) => {
    const raw = String(row[key] ?? '').trim().replace(/,/g, '');
    if (!raw) return false;
    return key === 'volume' ? !/^\d+(\.\d{1,2})?$/.test(raw) : !/^\d+$/.test(raw);
  });
}

export function totalOf(row, keys) {
  return keys.reduce((sum, key) => sum + (Number(String(row[key] ?? '').replace(/,/g, '')) || 0), 0);
}

function figures(row, keys) {
  return Object.fromEntries(keys.map((key) => [key, Number(String(row[key] ?? '').replace(/,/g, '')) || 0]));
}

/** What a row says is wrong, or ''. */
export function rowProblem(row, keys) {
  if (badKeys(row, keys).length) return keys.length > 1 ? 'Counts are whole numbers of people.' : 'Type a number.';
  return totalOf(row, keys) ? '' : 'Enter at least one person';
}

/** The save's body: the line's whole per-plan set, and the line figure when the card offers it. */
export function bodyFor({ keys, picked, rows, figure, offersFigure, on }) {
  const body = { on, plans: picked.map((id) => ({ id, enrollment: figures(rows[id] ?? {}, keys) })) };
  if (offersFigure) body.whole_line = totalOf(figure, keys) ? figures(figure, keys) : {};
  return body;
}

/** "20 EE · 5 ES · 3 EC · 2 FAM", "52 lives", "$1,250,000 volume" (the old countsText). */
export function countsText(found, keys) {
  if (!found) return '';
  if (keys.length === 1) {
    const value = Number(found[keys[0]] ?? 0).toLocaleString('en-US');
    return keys[0] === 'volume' ? `$${value} volume` : `${value} lives`;
  }
  return keys.filter((key) => Number(found[key])).map((key) => `${found[key]} ${key}`).join(' · ');
}

/** {key: {label, mark}} from /api/meta/ `enrollment.sources`. */
export function sourceWords(meta) {
  return Object.fromEntries((meta?.enrollment?.sources ?? []).map(({ key, ...words }) => [key, words]));
}

/** "Aetna HMO 1500, Cigna PPO and 3 more". */
export function namesOf(plans, ids) {
  const named = ids.map((id) => plans.find((plan) => plan.id === id)).filter(Boolean);
  const words = named.slice(0, MORE).map((plan) => `${plan.carrier} ${plan.name}`.trim());
  const more = named.length - words.length;
  if (more > 0) return `${words.join(', ')} and ${more} more`;
  return words.length > 1 ? `${words.slice(0, -1).join(', ')} and ${words.at(-1)}` : (words[0] ?? '');
}

/** What the line's census says, under the card (the old `bnf-pc-basis`). */
export function basisText(block, lineLabel) {
  const census = block?.census;
  if (!census) return `No census counts on ${lineLabel} yet.`;
  const lead = census.source === 'proxy' ? 'The medical census counts' : 'The census counts';
  return `${lead} ${countsText(census.figures, block.keys) || 'no one enrolled'} on ${lineLabel}.`;
}

/** The board-head button: "＋ Add summary medical tiers" until counts are typed, then "Summary tiers · On (2)". */
export function buttonLabel(block, lineLabel) {
  if (!block) return '';
  const what = block.keys.length > 1 ? 'tiers' : block.keys[0] === 'lives' ? 'lives' : 'volume';
  const typed = block.typed_plans + (block.figure ? 1 : 0);
  if (!typed) return `＋ Add summary ${lineLabel.toLowerCase()} ${what}`;
  return `Summary ${what} · ${block.on ? 'On' : 'Off'} (${typed})`;
}

/** {census text: plan id or ''} as the server matched them (F90). */
export function initialChoice(texts) {
  return Object.fromEntries((texts ?? []).map((row) => [row.text, row.plan_id ?? '']));
}

/** `census_names` for the save: each current plan's texts matched by hand (picked here, or by hand before), or null
 *  when nothing changed. A text matched by name or number needs no saving. */
export function namesBody(texts, currents, choice) {
  const rows = texts ?? [];
  const changed = rows.some((row) => (choice[row.text] ?? '') !== (row.plan_id ?? ''));
  if (!changed) return null;
  const byHand = (row) => choice[row.text] && (row.how === 'hand' || choice[row.text] !== row.plan_id);
  return Object.fromEntries(
    currents.map((plan) => [plan.id, rows.filter((row) => byHand(row) && choice[row.text] === plan.id).map((row) => row.text)]),
  );
}
