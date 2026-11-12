// A quote read's change set (plan.md §10.5; D.6's shape; D28, D31) as the review card draws it. Pure: no React.
//
// Plans come in the file's reading order (F138); each column says what the read would do with it (a new current
// plan, its renewal, a quote, values for a plan the deal has, or a current plan to pick). Rows follow the Advisor's
// field groups for the line (`meta.plans.line_groups`), showing only fields some plan in the read prints. Every
// figure is the server's; the only arithmetic here is the old card's "% move" between two printed numbers.

export const PLAN_OPS = new Set(['create_plan', 'set_values', 'pick_current']);
const ROLE_WORDS = { current: 'Current', renewal: 'Renewal', alternate: 'Quote' };

export function planItems(changeSet) {
  return (changeSet?.items || []).filter((item) => PLAN_OPS.has(item.op));
}

export function otherItems(changeSet) {
  return (changeSet?.items || []).filter((item) => !PLAN_OPS.has(item.op));
}

/** The ids ticked when the card opens: the server's ticks (stale and unsure items arrive unticked). */
export function initialPicks(changeSet) {
  return new Set((changeSet?.items || []).filter((item) => item.tick && !item.stale).map((item) => item.id));
}

/** [{line, items}] in reading order: a read can quote several lines side by side. */
export function byLine(items) {
  const out = [];
  items.forEach((item) => {
    const last = out[out.length - 1];
    const section = last && last.line === item.line ? last : out[out.push({ line: item.line, items: [] }) - 1];
    section.items.push(item);
  });
  return out;
}

/** [{group, label, rows: [{key, label, cells: {itemId: value entry}}]}] for the fields these items print. */
export function rowsFor(items, groups, fields) {
  const labels = Object.fromEntries((fields || []).map((field) => [field.key, field.label]));
  const valuesOf = Object.fromEntries(
    items.map((item) => [item.id, Object.fromEntries((item.values || []).map((value) => [value.key, value]))]),
  );
  const out = [];
  (groups || []).forEach((group) => {
    const rows = group.fields
      .filter((key) => items.some((item) => valuesOf[item.id][key]))
      .map((key) => ({
        key,
        label: labels[key] || key,
        cells: Object.fromEntries(items.map((item) => [item.id, valuesOf[item.id][key] || null])),
      }));
    if (rows.length) out.push({ group: group.key, label: group.label, rows });
  });
  return out;
}

/** Rows the file prints that fill no field (need 3): [{label, cells: {itemId: printed}}], in printed order. */
export function printedRows(items) {
  const rows = [];
  items.forEach((item) =>
    (item.unmapped || []).forEach((entry) => {
      let row = rows.find((r) => r.label === entry.label);
      if (!row) rows.push((row = { label: entry.label, cells: {} }));
      row.cells[item.id] = entry.printed;
    }),
  );
  return rows;
}

/** How far a number moved, as a signed percentage ('' unless both sides are numbers): the old StagedScanReview's. */
export function movedPct(oldVal, newVal) {
  const num = (v) => {
    const n = parseFloat(String(v ?? '').replace(/[^0-9.-]/g, ''));
    return Number.isFinite(n) ? n : null;
  };
  const before = num(oldVal);
  const after = num(newVal);
  if (before === null || after === null || before === 0) return '';
  const pct = ((after - before) / Math.abs(before)) * 100;
  if (Math.abs(pct) < 0.05) return '';
  return `${pct > 0 ? '+' : '−'}${Math.abs(pct).toFixed(1)}%`;
}

/** The chip over a plan's column: what using the read would do with it. */
export function headChip(item) {
  if (item.frozen) return { text: 'Sold — left as sold', tone: 'sold' };
  if (item.op === 'pick_current') return { text: 'Which current plan?', tone: 'sold' };
  if (item.op === 'set_values') return { text: item.values?.length ? 'Fills' : 'No change', tone: 'shortlist' };
  return { text: `NEW · ${ROLE_WORDS[item.role] || item.role}`, tone: 'shortlist' };
}

/** "Renews BlueOptions PPO 2500 (in this read)", "Replaces …", or ''. Labels come with the change set. */
export function linkText(item, items) {
  const named = (to) =>
    to?.item ? `${items.find((other) => other.id === to.item)?.name || 'a plan'} (in this read)` : to?.label || 'a plan';
  if (item.renews) return `Renews ${named(item.renews)}`;
  if (item.replaces?.to?.length) return `Replaces ${item.replaces.to.map(named).join(', ')}`;
  if (item.replaces?.text) return `Printed: ${item.replaces.text}`;
  return '';
}

/** How many ticked items "Apply N selected" would use. */
export function pickedCount(picks, changeSet) {
  return (changeSet?.items || []).filter((item) => picks.has(item.id)).length;
}
