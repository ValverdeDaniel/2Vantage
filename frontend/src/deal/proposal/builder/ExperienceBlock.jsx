import { useState } from 'react';
import { figureText, savedPeriods } from './dealCardsModel';

const blankPeriod = { period: '', premium: '', claims: '' };

/*
 * Plan experience on the Presentation pages card (plan.md §8.14; J45; the old PresentationPagesCard.jsx's block at
 * 891f1b3): the producer's summary of how the plan has run and up to six periods of premium and paid claims. Totals and
 * the producer's own words only — no names, no diagnoses, nothing about one person. The summary saves on blur
 * (`experience.summary`); a period saves on leaving a box (`experience.rows`, periods without a name dropped). The
 * server reads the typed figures ("$410,000") and refuses one it cannot.
 */
export default function ExperienceBlock({ experience, meta, busy, onSet }) {
  const [summary, setSummary] = useState(experience.summary);
  const [rows, setRows] = useState(experience.rows);
  const saved = JSON.stringify(experience.rows);
  const commitRows = (next) => {
    const clean = savedPeriods(next);
    if (JSON.stringify(clean) !== saved) onSet('experience.rows', clean);
  };
  const edit = (index, change) => setRows((now) => now.map((row, i) => (i === index ? { ...row, ...change } : row)));
  const box = (index, key, label, extra = {}) => (
    <input
      type="text"
      aria-label={label}
      placeholder={extra.placeholder ?? label}
      className={extra.className}
      maxLength={extra.maxLength}
      value={figureText(rows[index][key])}
      disabled={busy}
      onChange={(event) => edit(index, { [key]: event.target.value })}
      onBlur={() => commitRows(rows)}
    />
  );
  return (
    <div className="bnf-present-block">
      <div className="bnf-present-head">Plan experience</div>
      <div className="bnf-output-hint">
        Totals and your own summary only: no names, no diagnoses, nothing about one person.
      </div>
      <textarea
        className="bnf-present-summary"
        rows={2}
        maxLength={meta.limits.text}
        value={summary}
        disabled={busy}
        placeholder="How the plan has run, in a sentence or two."
        aria-label="How the plan has run"
        onChange={(event) => setSummary(event.target.value)}
        onBlur={() => summary.trim() !== experience.summary && onSet('experience.summary', summary.trim())}
      />
      {rows.length > 0 && (
        <div className="bnf-present-year bnf-present-cols" aria-hidden="true">
          <span className="bnf-present-col">Premium</span>
          <span className="bnf-present-col">Paid claims</span>
          <span>Period</span>
        </div>
      )}
      {rows.map((_row, index) => (
        // A period has no identity of its own until it is saved.
        <div key={index} className="bnf-present-year">
          {box(index, 'premium', 'Premium')}
          {box(index, 'claims', 'Paid claims')}
          {box(index, 'period', 'Period', {
            className: 'bnf-present-wide',
            maxLength: meta.limits.period,
            placeholder: 'January to December 2025',
          })}
          <button
            type="button"
            className="bnf-override-link"
            disabled={busy}
            onClick={() => {
              const next = rows.filter((_row, i) => i !== index);
              setRows(next);
              commitRows(next);
            }}
          >
            Remove
          </button>
        </div>
      ))}
      {rows.length < meta.limits.experience_rows && (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={busy}
          onClick={() => setRows((now) => [...now, blankPeriod])}
        >
          ＋ Add a period
        </button>
      )}
    </div>
  );
}
