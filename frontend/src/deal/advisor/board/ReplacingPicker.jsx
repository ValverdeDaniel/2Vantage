/*
 * "Replacing: [current plan ▾]" (plan.md §8.14; F52; the old PlanLinkPicker.jsx), on a line with two or more current
 * plans: which plan this quote replaces, so its change and its place in the client's documents follow. Beside every
 * presented quote, any quote already linked (bug 18: the old app showed it only beside starred or linked ones), and
 * any quote with no price until it says what it replaces (OQ20).
 * A renewal names the plan it renews; a quote replacing several (a consolidation) or a priced version only says so —
 * "Change role & links…" in the plan's ⋯ menu edits those. Saves through `plans/links/`.
 */
export default function ReplacingPicker({ plan, currents, busy, onChange }) {
  if (currents.length < 2 || plan.role === 'current') return null;
  const linked = plan.role === 'renewal' ? [plan.renews_id].filter(Boolean) : (plan.replaces_ids ?? []);
  // A quote that lost its price to a second current plan asks what it replaces (F88, OQ20).
  const asks = plan.premium?.reason === 'per_plan_counts_needed';
  if (!plan.presented && !linked.length && !asks) return null;
  const nameOf = (current) => `${current.carrier} — ${current.name}`;
  const fixed = plan.role === 'renewal' || linked.length > 1 || (plan.derived_from && plan.derived?.kind !== 'duplicate');
  if (fixed) {
    const names = linked.map((id) => currents.find((c) => c.id === id)).filter(Boolean).map(nameOf);
    return names.length ? <span className="bnf-link-picker-text">Replacing: {names.join(' + ')}</span> : null;
  }
  const value = linked[0] ?? '';
  const current = currents.find((c) => c.id === value);
  return (
    <label className={`bnf-link-picker${value ? '' : ' bnf-link-picker-open'}`}>
      <span>Replacing:</span>
      <select
        className="filter-select"
        value={value}
        disabled={busy}
        title={current ? nameOf(current) : 'Not linked: pick the current plan this quote replaces'}
        aria-label={`Which current plan ${plan.name} replaces`}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => onChange(plan, event.target.value ? [Number(event.target.value)] : [])}
      >
        <option value="">Pick a current plan</option>
        {currents.map((c) => (
          <option key={c.id} value={c.id}>
            {nameOf(c)}
          </option>
        ))}
      </select>
    </label>
  );
}
