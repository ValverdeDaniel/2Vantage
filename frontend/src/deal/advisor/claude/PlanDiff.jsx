import { displayValue } from '../../../lib/fieldValue';
import cx from '../../../ui/cx';
import { byLine, headChip, linkText, movedPct, printedRows, rowsFor } from './changeSet';

/*
 * The plans a quote read found, beside nothing yet on the deal (plan.md §10.5; D28; the old StagedScanReview's
 * QuoteDiff): one column per plan in the file's reading order (F138), its chip saying what using the read would do,
 * what it renews or replaces, and a tick; the Advisor's field groups as rows, each new value with "was …" and its
 * move, "not in the file" when the locator could not find it, and why a value is left alone. Rows the file prints
 * that fill no field close the table, greyed, with their printed text (need 3).
 */
const MOVES = new Set(['amount', 'rate', 'rate4', 'percent', 'number']);

function ValueCell({ entry, field }) {
  if (!entry) return <td className="bnf-cell bnf-staged-cell" />;
  const left = entry.why;
  const was = entry.old ? displayValue(field, entry.old) : '';
  const move = MOVES.has(field?.type) ? movedPct(entry.old, entry.new) : '';
  return (
    <td
      className={cx(
        'bnf-cell bnf-staged-cell',
        left ? 'bnf-staged-kept' : entry.old ? 'bnf-staged-changed' : 'bnf-staged-added',
      )}
      title={entry.low || left || (entry.page ? `Read on page ${entry.page}` : '')}
    >
      <span className="bb-cell-text">{displayValue(field, entry.new) || '—'}</span>
      {entry.loc?.state === 'absent' && (
        <span className="bnf-staged-absent" title="Code looked for this value in the file and it is printed nowhere">
          not in the file
        </span>
      )}
      {was && (
        <span className="bnf-staged-old" title="On the deal now">
          was {was}
          {move && <span className="bnf-staged-move"> · {move}</span>}
        </span>
      )}
      {left && <span className="bnf-staged-old">{left} — left alone</span>}
      {!left && entry.low && !entry.tick && <span className="bnf-staged-old">unsure — unticked</span>}
    </td>
  );
}

function PlanHead({ item, items, picked, onToggle }) {
  const chip = headChip(item);
  const link = linkText(item, items);
  return (
    <th data-item={item.id}>
      <div className="bnf-plan-head">
        <div>
          <span className={`bnf-plan-chip bnf-chip-${chip.tone}`}>{chip.text}</span>
          <div className="bnf-plan-carrier">{item.carrier}</div>
          <div className="bnf-plan-name">{item.name}</div>
          {item.plan_number && <div className="bnf-staged-line">Plan {item.plan_number}</div>}
          {link && <div className="bnf-staged-line">{link}</div>}
          {item.op === 'pick_current' && (
            <div className="bnf-staged-line" title={item.why}>
              One of: {item.options.map((option) => option.label).join(', ')}, or a new current plan
            </div>
          )}
          <label className="bnf-pchg-all">
            <input type="checkbox" checked={picked.has(item.id)} onChange={() => onToggle(item.id)} /> Use
          </label>
        </div>
      </div>
    </th>
  );
}

export default function PlanDiff({ items, meta, picked, onToggle }) {
  const fields = Object.fromEntries((meta.plans?.fields || []).map((field) => [field.key, field]));
  return byLine(items).map(({ line, items: lineItems }) => {
    const sections = rowsFor(lineItems, meta.plans?.line_groups?.[line], meta.plans?.fields);
    const printed = printedRows(lineItems);
    const span = lineItems.length + 1;
    return (
      <div className="bb-grid-card bb-mt" key={line} data-review-line={line}>
        <div className="bb-grid-scroll">
          <table className="bnf-compare-table">
            <thead>
              <tr>
                <th className="bnf-benefit-col">{meta.lines?.find((entry) => entry.key === line)?.label || line}</th>
                {lineItems.map((item) => (
                  <PlanHead key={item.id} item={item} items={items} picked={picked} onToggle={onToggle} />
                ))}
              </tr>
            </thead>
            <tbody>
              {sections.map((section) => [
                <tr key={`g-${section.group}`} className="bnf-group-row">
                  <td colSpan={span}>{section.label}</td>
                </tr>,
                ...section.rows.map((row) => (
                  <tr key={row.key}>
                    <td className="bnf-benefit-col">{row.label}</td>
                    {lineItems.map((item) => (
                      <ValueCell key={item.id} entry={row.cells[item.id]} field={fields[row.key]} />
                    ))}
                  </tr>
                )),
              ])}
              {printed.length > 0 && (
                <tr className="bnf-group-row">
                  <td colSpan={span}>As printed, no field</td>
                </tr>
              )}
              {printed.map((row) => (
                <tr key={`printed-${row.label}`} className="bb-empty">
                  <td className="bnf-benefit-col">{row.label}</td>
                  {lineItems.map((item) => (
                    <td key={item.id} className="bnf-cell">
                      {row.cells[item.id] || ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  });
}
