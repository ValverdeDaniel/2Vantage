import { useState } from 'react';
import { formatWhen, personName } from '../../lib/format';

/*
 * "Show removed files (N)" (plan.md §8.16; E16; OQ23): Remove archives a file, so it can come back. Each removed file
 * names who removed it and when, opens in the viewer, and has Restore. Only an admin purges (DELETE documents/{id}/).
 */
export default function RemovedFiles({ files, busy, onOpen, onRestore }) {
  const [open, setOpen] = useState(false);
  if (!files.length) return null;
  return (
    <div>
      <button type="button" className="bnf-linklike" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        {open ? 'Hide removed files' : `Show removed files (${files.length})`}
      </button>
      {open && (
        <div className="bnf-doc-edit-panel" role="region" aria-label="Removed files">
          {files.map((file) => (
            <div key={file.id} className="bnf-doc-editrow">
              <button type="button" className="bnf-linklike" onClick={() => onOpen(file.id)} title="Open this file">
                📄 {file.display_name || file.original_name}
              </button>
              <span className="bnf-doc-editmeta">
                Removed {formatWhen(file.archived_at)}
                {file.archived_by ? ` by ${personName(file.archived_by, '')}` : ''}
              </span>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                disabled={busy}
                onClick={() => onRestore(file)}
              >
                Restore
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
