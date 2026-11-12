import { useState } from 'react';
import ChipToggles from '../../ui/ChipToggles';

/*
 * The ✎ File panel (plan.md §8.16; E10–E13): rename, kind, role (only the kinds that ask, E13), carrier and lines.
 * Enter saves, Escape cancels; a blur saves nothing (tabbing name → kind → Save must not save three times). A kind
 * the file cannot be keeps the panel open with the server's sentence, and nothing is saved, not even the rename (E11).
 * A protected file (an issued proposal, a signed form) keeps its kind. The old panel's markup (bnf-doc-edit-*).
 */
export default function FilePanel({ file, meta, saving, error, onSave, onCancel }) {
  const [draft, setDraft] = useState({
    label: file.label || file.original_name,
    kind: file.kind,
    role: file.role,
    carrier: file.carrier,
    lines: file.lines,
  });
  const kinds = meta.document_kinds;
  const asksRole = kinds.find((k) => k.key === draft.kind)?.asks_role;
  const set = (key) => (value) => setDraft((d) => ({ ...d, [key]: value }));

  function save() {
    const label = draft.label.trim() === file.original_name ? '' : draft.label.trim();
    onSave({ ...draft, label, role: asksRole ? draft.role : '' });
  }
  const keys = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      save();
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      onCancel();
    }
  };

  return (
    <div className="bnf-doc-edit-panel">
      <div className="bnf-doc-editrow">
        <input
          className="bnf-doc-nameinput"
          value={draft.label}
          maxLength={200}
          autoFocus
          aria-label="Document name"
          onFocus={(event) => event.target.select()}
          onChange={(event) => set('label')(event.target.value)}
          onKeyDown={keys}
        />
        <select
          className="bnf-doc-typeselect"
          value={draft.kind}
          disabled={file.protected || saving}
          aria-label="Document type"
          onChange={(event) => set('kind')(event.target.value)}
          onKeyDown={(event) => event.key === 'Escape' && onCancel()}
        >
          {kinds.map((kind) => (
            <option key={kind.key} value={kind.key}>
              {kind.label}
            </option>
          ))}
        </select>
        {asksRole && (
          <select
            className="bnf-doc-typeselect"
            value={draft.role}
            disabled={saving}
            aria-label="What is this document?"
            onChange={(event) => set('role')(event.target.value)}
          >
            <option value="">What is this document?</option>
            {meta.document_roles.map((role) => (
              <option key={role.key} value={role.key}>
                {role.label}
              </option>
            ))}
          </select>
        )}
        <button type="button" className="btn btn-primary btn-sm bnf-doc-editsave" disabled={saving} onClick={save}>
          Save
        </button>
        <button type="button" className="bnf-doc-editcancel" onClick={onCancel}>
          Cancel
        </button>
      </div>
      <div className="bnf-doc-editrow">
        <input
          className="bnf-doc-nameinput"
          value={draft.carrier}
          maxLength={200}
          placeholder="Carrier this file is from (optional)"
          aria-label="Carrier this document is from"
          onChange={(event) => set('carrier')(event.target.value)}
          onKeyDown={keys}
        />
      </div>
      <div className="bnf-doc-editrow" aria-label="Lines it covers">
        <ChipToggles
          aria-label="Lines it covers"
          value={draft.lines}
          onChange={set('lines')}
          options={meta.lines.map((line) => ({ value: line.key, label: line.label }))}
        />
      </div>
      {error && (
        <div role="alert" className="error-message">
          {error}
        </div>
      )}
      <div className="bnf-doc-editmeta">
        File: {file.original_name}
        {file.protected && ' · an issued proposal or signed form keeps its type'}
        {' · naming the carrier lets a scan fill it in where the page never says it — a plan that names its own '}
        carrier still wins
      </div>
    </div>
  );
}
