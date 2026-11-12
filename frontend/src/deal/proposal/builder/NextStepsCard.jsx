import { useState } from 'react';
import BuilderCard from './BuilderCard';
import { savedSteps } from './dealCardsModel';

const blank = { text: '', date: '' };

/*
 * Next steps (plan.md §8.14; J67; the old NextStepsCard.jsx at 891f1b3, same words and classes): what the client does
 * next, and by when — a decision date, open enrollment, the effective date — in the producer's own words, on the
 * proposal's page before the closing page. Up to eight rows of date and text, saved on leaving a row (`next_steps`,
 * rows with no words dropped). The builder remounts it when the saved steps change.
 */
export default function NextStepsCard({ steps, meta, card, busy, onSet }) {
  const [rows, setRows] = useState(steps);
  const saved = JSON.stringify(steps);
  const commit = (next) => {
    const clean = savedSteps(next);
    if (JSON.stringify(clean) !== saved) onSet('next_steps', clean);
  };
  const edit = (index, change) => setRows((now) => now.map((row, i) => (i === index ? { ...row, ...change } : row)));
  return (
    <BuilderCard
      guide="build-next_steps"
      title="Next steps"
      summary={steps.length ? `${steps.length} on the proposal` : 'None yet'}
      card={card}
    >
      <div className="bb-panel-sub">What the client does next, and by when. Prints before the closing page.</div>
      {rows.map((row, index) => (
        // A row has no identity of its own until it is saved.
        <div key={index} className="bnf-build-step">
          <input
            type="date"
            aria-label="By when"
            value={row.date || ''}
            disabled={busy}
            onChange={(event) => edit(index, { date: event.target.value })}
            onBlur={() => commit(rows)}
          />
          <input
            type="text"
            maxLength={meta.limits.step_text}
            value={row.text}
            placeholder="Decide on the medical plan"
            aria-label="What happens"
            disabled={busy}
            onChange={(event) => edit(index, { text: event.target.value })}
            onBlur={() => commit(rows)}
          />
          <button
            type="button"
            className="bnf-override-link"
            disabled={busy}
            onClick={() => {
              const next = rows.filter((_row, i) => i !== index);
              setRows(next);
              commit(next);
            }}
          >
            Remove
          </button>
        </div>
      ))}
      {rows.length < meta.limits.next_steps && (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={busy}
          onClick={() => setRows((now) => [...now, blank])}
        >
          ＋ Add a step
        </button>
      )}
    </BuilderCard>
  );
}
