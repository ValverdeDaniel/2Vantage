import { intakeRows } from './intakeRows';

/*
 * An intake read's body in the review card (plan.md §10.5; B40, D112; the old StagedScanReview's IntakeDiff): the
 * answers the file gives, beside what the deal holds (the old Field · New scan · Current table, `bnf-compare-table`),
 * then the coverage in force it would add or fill, then the contacts it would add. Each row has its tick; an answer a
 * person stands behind, or one Claude was unsure of, arrives unticked and says why (B39's rule, D61). ↗ opens the
 * value's page on Documents.
 */
function Tick({ item, picked, onToggle }) {
  return (
    <input
      type="checkbox"
      aria-label={`Use ${item.label || item.name}`}
      checked={picked.has(item.id)}
      onChange={() => onToggle(item.id)}
    />
  );
}

export default function IntakeReview({ changeSet, picked, onToggle, onOpen }) {
  const { answers, coverage, contacts } = intakeRows(changeSet);
  return (
    <>
      {answers.length > 0 && (
        <div className="bb-grid-card bb-mt">
          <table className="bnf-compare-table">
            <thead>
              <tr>
                <th aria-label="Use" />
                <th className="bnf-benefit-col">Field</th>
                <th>New scan</th>
                <th>Current</th>
              </tr>
            </thead>
            <tbody>
              {answers.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Tick item={item} picked={picked} onToggle={onToggle} />
                  </td>
                  <td className="bnf-benefit-col">
                    {item.label}
                    {item.why ? <div className="bnf-staged-scope-note">{item.why}</div> : null}
                  </td>
                  <td className="bnf-cell bnf-staged-changed" title={item.low || undefined}>
                    {item.shown}
                    {item.page && onOpen ? (
                      <button
                        type="button"
                        className="bnf-src-pin"
                        title={`See it on page ${item.page} of the file`}
                        onClick={() => onOpen(item.doc, item.page)}
                      >
                        ↗
                      </button>
                    ) : null}
                  </td>
                  <td className="bnf-cell bb-empty">{item.was}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {coverage.length > 0 && (
        <div className="bnf-staged-section">
          <div className="bnf-staged-section-title">Current coverage</div>
          <ul className="bnf-staged-list">
            {coverage.map((item) => (
              <li key={item.id}>
                <Tick item={item} picked={picked} onToggle={onToggle} /> {item.text}
              </li>
            ))}
          </ul>
        </div>
      )}
      {contacts.length > 0 && (
        <div className="bnf-staged-section">
          <div className="bnf-staged-section-title">Contacts</div>
          <ul className="bnf-staged-list">
            {contacts.map((item) => (
              <li key={item.id}>
                <Tick item={item} picked={picked} onToggle={onToggle} /> {item.text}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
