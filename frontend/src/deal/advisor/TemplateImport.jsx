import { useState } from 'react';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import { useToast } from '../../ui/useToast';
import styles from './AdvisorTab.module.css';

/** Import the filled plan template: file → dry run → Import (plan.md §8.11, §9.3). All or nothing. */
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
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={!ready} busy={importTemplate.isPending} onClick={apply}>
            Import
          </Button>
        </>
      }
    >
      <Field label="Filled plan template (.xlsx)">
        <input type="file" accept=".xlsx" onChange={(event) => dryRun(event.target.files?.[0] ?? null)} />
      </Field>
      {importTemplate.isPending && !check && <p>Checking…</p>}
      {failure && <p role="alert">{failure}</p>}
      {check && !check.errors?.length && (
        <p role="status">
          {check.create || check.update
            ? `${check.create} plans to create, ${check.update} to update (${check.cells_changed} cells change).`
            : 'Nothing in this file changes the plans.'}
        </p>
      )}
      {check?.errors?.length > 0 && (
        <div role="alert">
          <p>Nothing was imported. Fix these cells and try again:</p>
          <ul className={styles.errorList}>
            {check.errors.map((error, index) => (
              <li key={index}>
                {[error.sheet, error.cell].filter(Boolean).join('!')}
                {error.sheet || error.cell ? ': ' : ''}
                {error.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Modal>
  );
}
