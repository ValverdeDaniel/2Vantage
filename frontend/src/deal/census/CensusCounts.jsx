import { lineLabel } from '../../api/meta';

const BUCKETS = [
  { key: 'EE', label: 'EE' },
  { key: 'ES', label: 'ES' },
  { key: 'EC', label: 'EC' },
  { key: 'FAM', label: 'FAM' },
  { key: 'waived', label: 'Waived' },
  { key: 'blank', label: 'Blank' },
];

function Row({ label, counts }) {
  return (
    <tr>
      <td className="bnf-benefit-col">{label}</td>
      {BUCKETS.map((bucket) => (
        <td key={bucket.key}>{counts[bucket.key] ?? 0}</td>
      ))}
    </tr>
  );
}

/*
 * What the census counts, as the pricing will read it (plan.md §5.3.6; C39–C46): each line's tier counts from the
 * employees (dependents are never counted; a worksite line borrows medical's), and on medical, dental and vision the
 * counts per plan name the census gives — the per-plan counts a person would otherwise count and retype. Matching the
 * plan names to the current plans is the Advisor's (slice 13). Read-only, in the old comparison table's frame and its
 * scroller (`bb-grid-scroll`), so a narrow window scrolls the table, not the page.
 */
export default function CensusCounts({ meta, rollup, derived }) {
  const lines = Object.entries(rollup || {}).filter(([, figures]) => 'EE' in figures);
  if (!lines.length) return null;
  return (
    <div className="bb-panel">
      <div className="bb-panel-title">Enrollment from the census</div>
      <div className="bb-subtitle">
        Employees by tier on each line, then by the plan each one names.
        {derived?.fte != null && ` Full-time (${derived.hours_threshold}+ hours a week): ${derived.fte}.`}
        {derived?.aged_65 != null && ` Aged 65 or more on ${derived.as_of}: ${derived.aged_65}.`}
      </div>
      <div className="bb-grid-scroll bb-mt">
        <table className="bnf-compare-table">
          <thead>
            <tr>
              <th className="bnf-benefit-col">Line · plan named</th>
              {BUCKETS.map((bucket) => (
                <th key={bucket.key}>{bucket.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lines.map(([line, figures]) => [
              <Row
                key={line}
                label={`${lineLabel(meta, line)}${figures.source === 'borrowed' ? ' (borrowed from medical)' : ''}`}
                counts={figures}
              />,
              ...Object.entries(figures.by_plan || {}).map(([text, counts]) => (
                <Row key={`${line}:${text}`} label={`↳ ${text || '(no plan named)'}`} counts={counts} />
              )),
            ])}
          </tbody>
        </table>
      </div>
    </div>
  );
}
