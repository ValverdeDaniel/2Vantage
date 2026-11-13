import { partValue, withPart } from './askCardModel';

/*
 * The parts of the picked link's form on this tab (plan.md §8.8; L42; old 891f1b3 `RequestRail.jsx` `PartTick`, the
 * tick on a tab): what the whole intake asks (off, what marketing needs, every blank, the whole form), the census
 * (off, the required gaps, every blank, the whole census) and their census file, the checklist's missing documents.
 * Picked questions stay ticks in the list below. Each change waits for Update link. Words from /api/meta/ `review`.
 */
function Scope({ label, value, options, picked, onChange, disabled }) {
  return (
    <label className="rr-part">
      <span className="rr-parts-h">{label}</span>
      <select value={value} aria-label={label} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
        <option value="">Off</option>
        {picked && <option value="selected">Only the questions ticked below</option>}
        {options.map((option) => (
          <option key={option.key} value={option.key}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function Tick({ label, checked, onChange, disabled }) {
  return (
    <label className="rr-part rr-part-tick">
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

export default function AskParts({ pane, meta, target, change, onChange, disabled }) {
  const set = (part, value) => onChange(withPart(change, target, part, value));
  const intake = partValue(target, change, 'intake');
  return (
    <div className="rr-parts" aria-label="What this link asks on this tab">
      {pane === 'intake' && (
        <Scope label="Intake" value={intake} options={meta?.intake_scopes || []} disabled={disabled}
          picked={target.parts.intake === 'selected'} onChange={(value) => set('intake', value === 'selected' ? 'selected' : value)} />
      )}
      {pane === 'census' && (
        <>
          <Scope label="Census" value={partValue(target, change, 'census')} options={meta?.census_scopes || []} disabled={disabled}
            picked={target.parts.census === 'selected'} onChange={(value) => set('census', value)} />
          <Tick label="Their census file" checked={partValue(target, change, 'census_file')} disabled={disabled}
            onChange={(value) => set('census_file', value)} />
        </>
      )}
      {pane === 'documents' && (
        <Tick label="Any documents the checklist still needs" checked={partValue(target, change, 'documents_missing')}
          disabled={disabled} onChange={(value) => set('documents_missing', value)} />
      )}
    </div>
  );
}
