import { useState } from 'react';
import { formErrorText } from '../../lib/errors';

/*
 * "File as" (plan.md §8.16; E4–E6, D-096): files dropped on the tab (or chosen) wait here until each says what it is,
 * from Daniel's six (the kinds marked `file_as`); then each is uploaded under its kind, one per request. A file the
 * kind does not take, or over the size cap, keeps its row with the server's sentence. The old drawer's markup
 * (bnf-scanchat-fileas*); the drawer itself is slice 20's, which moves this list there.
 */
export default function FileAsList({ pending, meta, upload, onChange, onDone }) {
  const [busy, setBusy] = useState(false);
  if (!pending.length) return null;
  const choices = meta.document_kinds.filter((kind) => kind.file_as);
  const missing = pending.some((item) => !item.kind);
  const setRow = (index, change) => onChange(pending.map((item, i) => (i === index ? { ...item, ...change } : item)));

  async function send() {
    setBusy(true);
    const left = [];
    let done = 0;
    for (const item of pending) {
      try {
        await upload.mutateAsync({ file: item.file, kind: item.kind });
        done += 1;
      } catch (error) {
        left.push({ ...item, error: formErrorText(error) });
      }
    }
    setBusy(false);
    onChange(left);
    if (done) onDone(done);
  }

  return (
    <div className="bnf-scanchat-fileas">
      <div className="bnf-scanchat-fileas-head">Say what each file is — it is filed and read by that type:</div>
      {pending.map((item, index) => (
        <div key={`${item.file.name}-${index}`}>
          <div className="bnf-scanchat-fileas-row">
            <span className="bnf-scanchat-fileas-name" title={item.file.name}>
              📄 {item.file.name}
            </span>
            <select
              className="bnf-scanchat-doctype"
              value={item.kind}
              disabled={busy}
              aria-label={`File ${item.file.name} as`}
              onChange={(event) => setRow(index, { kind: event.target.value, error: '' })}
            >
              <option value="">File as…</option>
              {choices.map((kind) => (
                <option key={kind.key} value={kind.key}>
                  {kind.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="bnf-scanchat-fileas-drop"
              onClick={() => onChange(pending.filter((_item, i) => i !== index))}
              disabled={busy}
              title="Leave this file out"
              aria-label={`Leave ${item.file.name} out`}
            >
              ✕
            </button>
          </div>
          {item.error && (
            <div role="alert" className="error-message">
              {item.error}
            </div>
          )}
        </div>
      ))}
      <button
        type="button"
        className="btn btn-primary btn-sm"
        disabled={busy || missing}
        onClick={send}
        title={missing ? 'Pick a type for every file first' : 'Upload the files under the types you picked'}
      >
        Upload {pending.length} file{pending.length === 1 ? '' : 's'} ▸
      </button>
    </div>
  );
}
