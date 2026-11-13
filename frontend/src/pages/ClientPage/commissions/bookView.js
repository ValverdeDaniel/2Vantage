// The client Commissions tab's pure view logic (plan.md §8.5; CL25, H106; old Vantage 891f1b3
// `radar/client/ClientCommissionsTab.jsx`): the plan-year groups with their records in the server's order, the
// year-over-year words, and which rows are no longer live. Every figure is the server's (rule 5); nothing here sums.

/** [{...year, rows}] in the server's order (newest year first), each year's records in the Book's order. */
export function yearGroups(book) {
  const byId = new Map((book?.rows || []).map((row) => [row.id, row]));
  return (book?.years || []).map((year) => ({
    ...year,
    rows: year.records.map((id) => byId.get(id)).filter(Boolean),
  }));
}

/** "▲ 5% vs 2026" / "▼ 3% vs 2026" against the year below it, or '' (the old group header's delta). */
export function changeWords(year, below) {
  if (year.change_pct == null) return '';
  const arrow = year.change_pct >= 0 ? '▲' : '▼';
  return `${arrow} ${Math.abs(year.change_pct)}%${below ? ` vs ${below.label}` : ''}`;
}

/** True when a record is no longer live (renewed, terminated, lost BOR): its line shows its status. */
export function inactive(row, meta) {
  const live = meta?.commission?.live_statuses || ['booked', 'active'];
  return !live.includes(row.status);
}

/** "1 hole" / "2 holes" for a year's records booked without a rate or premium. */
export function holeWords(count) {
  return `${count} hole${count === 1 ? '' : 's'}`;
}
