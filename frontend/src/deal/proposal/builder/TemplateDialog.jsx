import { useState } from 'react';
import Modal from '../../../ui/Modal';

/*
 * "Save as a template" / "Update template" (plan.md §8.14; J68; the old TemplateBar's modal at 891f1b3, `bnf-saved-
 * modal`): a name, what it is for, this line or any line, and Share with the team. It stores the part exactly as it
 * is now; the server cleans it and answers each refused field, shown under its input. `line` '' is any line.
 */
export default function TemplateDialog({ form, kindLabel, lineLabel, placeholders, busy, onClose, onSubmit }) {
  const [draft, setDraft] = useState(form);
  const errors = form.errors ?? {};
  const change = (patch) => setDraft((now) => ({ ...now, ...patch }));
  return (
    <Modal
      open
      size="sm"
      onClose={onClose}
      onSubmit={() => onSubmit(draft)}
      title={draft.id ? 'Update template' : 'Save as a template'}
      sub={`Stores the ${kindLabel.toLowerCase()} exactly as it is now, so the next client starts from it instead of from nothing.`}
      hint={draft.id ? 'Overwrites the stored template.' : 'Saved to your list.'}
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
          <input value={draft.name} maxLength={80} placeholder={placeholders.name} onChange={(event) => change({ name: event.target.value })} />
          {errors.name && <em className="bnf-saved-error">{errors.name}</em>}
        </label>
        <label className="bnf-saved-field">
          <span>
            What it is for <i>(optional)</i>
          </span>
          <input
            value={draft.description}
            maxLength={200}
            placeholder={placeholders.purpose}
            onChange={(event) => change({ description: event.target.value })}
          />
          {errors.description && <em className="bnf-saved-error">{errors.description}</em>}
        </label>
        <label className="bnf-saved-field">
          <span>Offer it on</span>
          <select className="filter-select" value={draft.line} onChange={(event) => change({ line: event.target.value })}>
            <option value="">Any line of business</option>
            {draft.lineKey && <option value={draft.lineKey}>{lineLabel} only</option>}
          </select>
        </label>
        <label className="bnf-filter-check bnf-saved-share">
          <input type="checkbox" checked={draft.shared} onChange={(event) => change({ shared: event.target.checked })} />
          Share with the team — everyone can use it, only you can change it
        </label>
      </div>
    </Modal>
  );
}
