import { useState } from 'react';

/*
 * Expected enrollment on one line (plan.md §5.5, §8.14; J48, kept by OQ18; the old EnrollmentStrip.jsx at 891f1b3).
 * It shows the line's people and where they come from (typed for the line, the census, borrowed from medical…; the
 * server's words), and types the figure for the whole line through quotes' one enrollment door (`set_enrollment`
 * `whole_line`) where that figure prices the line: one current plan at most and no plan typed on its own, or a figure
 * already stored (F88). Elsewhere the Advisor's counts card splits the counts. A later census import wins (F91).
 */

// "30 EE · 8 ES", "52 lives", "1250000 volume", as the old strip wrote the tiers.
const countsText = (keys, figures) =>
  keys
    .filter((key) => figures?.[key])
    .map((key) => `${figures[key]} ${key}`)
    .join(' · ');

function EnrollmentForm({ keys, labels, initial, busy, onSave, onCancel }) {
  const [draft, setDraft] = useState(() =>
    Object.fromEntries(keys.map((key) => [key, initial?.[key] ? String(initial[key]) : ''])),
  );
  const pattern = (key) => (key === 'volume' ? /^\d+(\.\d+)?$/ : /^\d+$/);
  const bad = keys.filter((key) => draft[key].trim() !== '' && !pattern(key).test(draft[key].trim()));
  const total = keys.reduce((sum, key) => sum + (Number(draft[key]) || 0), 0);
  const submit = (event) => {
    event.preventDefault();
    if (bad.length || !total) return;
    onSave(Object.fromEntries(keys.map((key) => [key, Number(draft[key]) || 0])));
  };
  return (
    <form className="bnf-build-enroll-form" onSubmit={submit}>
      {keys.map((key) => (
        <label key={key} title={labels[key]}>
          <span>{key === 'volume' || key === 'lives' ? labels[key] : key}</span>
          <input
            type="number"
            min="0"
            step={key === 'volume' ? 'any' : '1'}
            inputMode="numeric"
            value={draft[key]}
            aria-label={`${labels[key] ?? key}: expected enrollment`}
            aria-invalid={bad.includes(key) || undefined}
            onChange={(event) => setDraft((now) => ({ ...now, [key]: event.target.value }))}
          />
        </label>
      ))}
      <button
        type="submit"
        className="btn btn-primary btn-sm"
        disabled={busy || bad.length > 0 || !total}
        title={!total ? 'Enter at least one person' : undefined}
      >
        Save
      </button>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onCancel}>
        Cancel
      </button>
      {bad.length > 0 && (
        <span className="bnf-build-enroll-bad" role="alert">
          Whole numbers of people only
        </span>
      )}
    </form>
  );
}

export default function EnrollmentStrip({ line, labels, busy, onSave, onAdvisor }) {
  const [editing, setEditing] = useState(false);
  const strip = line.enrollment;
  const own = Boolean(strip.typed) && strip.source === 'line';
  const shown = countsText(strip.keys, strip.figures);
  const lead = own ? 'Expected enrollment' : shown ? strip.words || 'Enrollment' : 'No enrollment yet';
  const save = (figures) => {
    setEditing(false);
    onSave(figures);
  };
  return (
    <div className={`bnf-build-enroll${shown ? '' : ' is-empty'}`} data-enroll-line={line.line}>
      <div className="bnf-build-enroll-head">
        <span>
          <b>
            {lead}
            {shown ? ':' : '.'}
          </b>{' '}
          {shown || 'The monthly totals, cost summary and recommendation print blank until this line has one.'}
          {own && (
            <span className="bnf-build-enroll-note">
              {' '}
              Typed for this line; the client&apos;s documents say &quot;(expected)&quot;.
            </span>
          )}
          {!strip.editable && (
            <span className="bnf-build-enroll-note">
              {' '}
              {strip.several
                ? 'This line has several current plans: split its counts between them in the Advisor.'
                : 'Its plans carry their own counts: edit them in the Advisor.'}
            </span>
          )}
        </span>
        {!editing && (
          <span className="bnf-build-enroll-actions">
            {strip.editable ? (
              <>
                <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => setEditing(true)}>
                  {own ? 'Edit' : 'Enter expected enrollment'}
                </button>
                {strip.typed && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={busy}
                    title="Remove the typed counts: the line goes back to its census, if it has one"
                    onClick={() => onSave({})}
                  >
                    Clear
                  </button>
                )}
              </>
            ) : (
              <button type="button" className="btn btn-secondary btn-sm" onClick={onAdvisor}>
                Edit counts in the Advisor ▸
              </button>
            )}
          </span>
        )}
      </div>
      {editing && (
        <EnrollmentForm
          keys={strip.keys}
          labels={labels}
          initial={strip.typed ?? strip.figures}
          busy={busy}
          onSave={save}
          onCancel={() => setEditing(false)}
        />
      )}
    </div>
  );
}
