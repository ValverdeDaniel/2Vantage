import { useState } from 'react';
import { formErrorText } from '../../lib/errors';
import Button from '../../ui/Button';
import ChipToggles from '../../ui/ChipToggles';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import Select from '../../ui/Select';
import TextInput from '../../ui/TextInput';

const ROLE_KINDS = ['quote', 'renewal', 'sbc'];

function MetaFields({ meta, value, onChange }) {
  const set = (key) => (next) => onChange({ ...value, [key]: next });
  return (
    <>
      <Field label="Kind">
        <Select
          value={value.kind}
          onChange={(event) => set('kind')(event.target.value)}
          options={meta.document_kinds.map((k) => ({ value: k.key, label: k.label }))}
        />
      </Field>
      {ROLE_KINDS.includes(value.kind) && (
        <Field label="What is this document?">
          <Select
            value={value.role}
            placeholder="Not said"
            onChange={(event) => set('role')(event.target.value)}
            options={meta.document_roles.map((r) => ({ value: r.key, label: r.label }))}
          />
        </Field>
      )}
      <Field label="Carrier">
        <TextInput value={value.carrier} onChange={(event) => set('carrier')(event.target.value)} />
      </Field>
      <Field label="Lines it covers" group>
        <ChipToggles
          value={value.lines}
          onChange={set('lines')}
          options={meta.lines.map((line) => ({ value: line.key, label: line.label }))}
        />
      </Field>
    </>
  );
}

const blank = { kind: 'other', role: '', carrier: '', lines: [], label: '' };

/** Upload one or several files; each gets its own kind, role, carrier and lines (plan.md §8.16). */
export function UploadDialog({ open, onClose, meta, upload, onDone }) {
  return open ? <UploadForm onClose={onClose} meta={meta} upload={upload} onDone={onDone} /> : null;
}

function UploadForm({ onClose, meta, upload, onDone }) {
  const [items, setItems] = useState([]);
  const [failed, setFailed] = useState('');

  function choose(files) {
    setItems([...files].map((file) => ({ file, meta: { ...blank } })));
  }

  async function submit() {
    setFailed('');
    let done = 0;
    for (const item of items) {
      try {
        await upload.mutateAsync({ file: item.file, ...item.meta });
        done += 1;
      } catch (error) {
        setFailed(`${item.file.name}: ${formErrorText(error)}`);
        break;
      }
    }
    if (done) onDone(done);
    if (done === items.length) onClose();
    else setItems(items.slice(done));
  }

  return (
    <Modal
      open
      size="lg"
      title="Upload documents"
      sub="PDF, Excel, CSV, images, Word, text or email, up to 50 MB each."
      onClose={onClose}
      onSubmit={() => submit()}
      footer={
        <>
          <Button size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" type="submit" variant="primary" disabled={!items.length} busy={upload.isPending}>
            Upload {items.length > 1 ? `${items.length} files` : ''}
          </Button>
        </>
      }
    >
      <Field label="Files">
        <input type="file" multiple onChange={(event) => choose(event.target.files ?? [])} />
      </Field>
      {items.map((item, index) => (
        <fieldset key={`${item.file.name}-${index}`} className="bb-panel bb-mb">
          <legend className="bb-panel-title">{item.file.name}</legend>
          <MetaFields
            meta={meta}
            value={item.meta}
            onChange={(next) => setItems((prev) => prev.map((it, i) => (i === index ? { ...it, meta: next } : it)))}
          />
        </fieldset>
      ))}
      {failed && (
        <div role="alert" className="error-message">
          {failed}
        </div>
      )}
    </Modal>
  );
}

/** Edit a document's label, kind, role, carrier and lines. */
export function EditDialog({ document, onClose, meta, update }) {
  return document ? <EditForm document={document} onClose={onClose} meta={meta} update={update} /> : null;
}

function EditForm({ document, onClose, meta, update }) {
  const [value, setValue] = useState({
    kind: document.kind,
    role: document.role,
    carrier: document.carrier,
    lines: document.lines,
    label: document.label,
  });

  async function submit() {
    await update.mutateAsync({ documentId: document.id, changes: value });
    onClose();
  }

  return (
    <Modal
      open
      title={`Edit ${document.label || document.original_name}`}
      onClose={onClose}
      onSubmit={() => submit().catch(() => {})}
      footer={
        <>
          <Button size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" type="submit" variant="primary" busy={update.isPending}>
            Save
          </Button>
        </>
      }
    >
      <Field label="Label" help="Blank shows the file name.">
        <TextInput value={value.label} onChange={(event) => setValue({ ...value, label: event.target.value })} />
      </Field>
      <MetaFields meta={meta} value={value} onChange={setValue} />
      {update.error && (
        <div role="alert" className="error-message">
          {formErrorText(update.error)}
        </div>
      )}
    </Modal>
  );
}
