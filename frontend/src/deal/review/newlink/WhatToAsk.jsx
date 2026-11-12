import { NOTHING } from './newLinkModel';

/*
 * What to ask, the minimal way (L40, L46; slice 57 brings the full Ask list with its ticks): the intake by scope, the
 * census by scope and its file, and any documents the checklist still needs. The choices' words come from /api/meta/
 * `review` (rule 1); what each scope asks is worked out on the server when the client opens the link.
 */
function ScopeSelect({ label, value, options, onChange, disabled }) {
  return (
    <label className="rr-edit-row">
      <b className="rr-edit-note">{label}</b>
      <select value={value} aria-label={label} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
        <option value={NOTHING}>Nothing</option>
        {options.map((option) => (
          <option key={option.key} value={option.key}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function WhatToAsk({ meta, state, onChange, disabled }) {
  return (
    <div className="rr-newlink-levels">
      <ScopeSelect label="Intake" value={state.intake} options={meta?.intake_scopes || []} disabled={disabled}
        onChange={(intake) => onChange({ intake })} />
      <ScopeSelect label="Census" value={state.census} options={meta?.census_scopes || []} disabled={disabled}
        onChange={(census) => onChange({ census })} />
      <label className="rr-edit-level">
        <input type="checkbox" checked={state.censusFile} disabled={disabled}
          onChange={(e) => onChange({ censusFile: e.target.checked })} />
        <span>
          <b>Their census file</b> They upload their own spreadsheet, and we read it.
        </span>
      </label>
      <label className="rr-edit-level">
        <input type="checkbox" checked={state.documents} disabled={disabled}
          onChange={(e) => onChange({ documents: e.target.checked })} />
        <span>
          <b>Any missing documents</b> What the marketing checklist still needs from them.
        </span>
      </label>
    </div>
  );
}
