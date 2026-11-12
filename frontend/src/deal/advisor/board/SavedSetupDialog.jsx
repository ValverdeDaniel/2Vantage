import { useState } from 'react';
import Modal from '../../../ui/Modal';

/*
 * "Save this setup" / "Update saved setup" (plan.md §8.14; F28; the old SavedFilterBar's modal, `bnf-saved-modal`):
 * a name, what it is for, this line or any line, and Share with the team. It stores the board exactly as it is now;
 * the server cleans it and answers each refused field, shown under its input. `line` '' is any line.
 */
export default function SavedSetupDialog({ form, lineLabel, busy, onClose, onSubmit }) {
  const [draft, setDraft] = useState(form);
  const errors = form.errors ?? {};
  const change = (patch) => setDraft((now) => ({ ...now, ...patch }));
  return (
    <Modal
      open
      size="sm"
      onClose={onClose}
      onSubmit={() => onSubmit(draft)}
      title={draft.id ? 'Update saved setup' : 'Save this setup'}
      sub="Stores the filters, the columns and the sort exactly as they are now, for quote comparison."
      hint={draft.id ? 'Overwrites the stored setup.' : 'Saved to your list.'}
      footer={
        <>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary btn-sm" disabled={busy}>
            {busy ? 'Saving…' : 'Save'}
          </button>
        </>
      }
    >
      <div className="bb-custom-form">
        <label className="bnf-saved-field">
          <span>Name</span>
          <input
            value={draft.name}
            maxLength={80}
            placeholder="Budget-conscious medical"
            onChange={(event) => change({ name: event.target.value })}
          />
          {errors.name && <em className="bnf-saved-error">{errors.name}</em>}
        </label>
        <label className="bnf-saved-field">
          <span>
            What it is for <i>(optional)</i>
          </span>
          <input
            value={draft.description}
            maxLength={200}
            placeholder="Within 10% of current, nothing low-confidence"
            onChange={(event) => change({ description: event.target.value })}
          />
          {errors.description && <em className="bnf-saved-error">{errors.description}</em>}
        </label>
        <label className="bnf-saved-field">
          <span>Offer it on</span>
          <select className="filter-select" value={draft.line} onChange={(event) => change({ line: event.target.value })}>
            {draft.lineKey && <option value={draft.lineKey}>{lineLabel} only</option>}
            <option value="">Any line of business</option>
          </select>
        </label>
        <label className="bnf-filter-check bnf-saved-share">
          <input type="checkbox" checked={draft.shared} onChange={(event) => change({ shared: event.target.checked })} />
          Share with the team — everyone can use it, only you can change it
        </label>
        {errors.config && (
          <em className="bnf-saved-error">
            This setup could not be stored: {typeof errors.config === 'object' ? Object.values(errors.config).join(' ') : errors.config}
          </em>
        )}
      </div>
    </Modal>
  );
}
