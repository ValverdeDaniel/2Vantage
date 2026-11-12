import { useState } from 'react';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import { useToast } from '../../ui/useToast';

/** Import the filled plan template: file → dry run → Import (plan.md §8.14, §9.3). All or nothing. */
export default function TemplateImport({ open, onClose, importTemplate }) {
  return open ? <ImportForm onClose={onClose} importTemplate={importTemplate} /> : null;
}

function ImportForm({ onClose, importTemplate }) {
  const toast = useToast();
  const [file, setFile] = useState(null);
  const [check, setCheck] = useState(null);
  const [failure, setFailure] = useState('');

  async function dryRun(next) {
    setFile(next);
    setCheck(null);
    setFailure('');
    if (!next) return;
    try {
      setCheck(await importTemplate.mutateAsync({ file: next, dryRun: true }));
    } catch (error) {
      setFailure(errorText(error));
    }
  }

  async function apply() {
    try {
      const result = await importTemplate.mutateAsync({ file, dryRun: false });
      if (result.errors?.length) {
        setCheck(result);
        return;
      }
      toast.success(`Imported: ${result.create} created, ${result.update} updated, ${result.cells_changed} cells`);
      onClose();
    } catch (error) {
      setFailure(errorText(error));
    }
  }

  const ready = check && !check.errors?.length && (check.create || check.update);
  return (
    <Modal
      open
      title="Import plan template"
      onClose={onClose}
      footer={
        <>
          <Button size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" variant="primary" disabled={!ready} busy={importTemplate.isPending} onClick={apply}>
            Import
          </Button>
        </>
      }
    >
      <Field label="Filled plan template (.xlsx)">
        <input type="file" accept=".xlsx" onChange={(event) => dryRun(event.target.files?.[0] ?? null)} />
      </Field>
      {importTemplate.isPending && !check && <div className="bnf-packet-note">Checking…</div>}
      {failure && (
        <div role="alert" className="error-message">
          {failure}
        </div>
      )}
      {check && !check.errors?.length && (
        <div role="status" className="bnf-packet-note">
          {check.create || check.update
            ? `${check.create} plans to create, ${check.update} to update (${check.cells_changed} cells change).`
            : 'Nothing in this file changes the plans.'}
        </div>
      )}
      {check?.errors?.length > 0 && (
        <div role="alert" className="bnf-build-checks">
          <div className="bnf-build-checks-head">
            <b>Nothing was imported. Fix these cells and try again:</b>
          </div>
          <ul className="bnf-build-checks-list">
            {check.errors.map((error, index) => (
              <li key={index} className="bnf-build-check bnf-build-check-stop">
                {(error.sheet || error.cell) && (
                  <span className="bnf-build-check-level">{[error.sheet, error.cell].filter(Boolean).join('!')}</span>
                )}
                <span className="bnf-build-check-msg">{error.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Modal>
  );
}
