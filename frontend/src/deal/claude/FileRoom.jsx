import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useUpdateDocument } from '../../api/documents';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import FileAsList from '../documents/FileAsList';
import { readButton, readKinds } from './drawerWords';

/*
 * The File room (plan.md §8.17; D14; the old ScanChat's Documents rows, D-096): where each file says what it is
 * before it is filed — the "File as" list, "Upload N files ▸", which then reads what it filed — and every file on the
 * deal as a row: a tick for the files Claude reads, the name (it opens the file on Documents; "👁 open" marks the one
 * on screen there), what it is filed as, and "scanned" once a read has read it. One button reads the ticked files:
 * "📥 Read N files into the table", landing by the person (D71). The newest file not read yet starts ticked.
 */
export default function FileRoom({ dealId, files, meta, readIds, reading, attach }) {
  const toast = useToast();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const update = useUpdateDocument(dealId);
  const readable = readKinds(meta);
  const live = files.filter((file) => !file.archived_at);
  const unread = live.filter(
    (file) => readable.includes(file.kind) && !readIds.includes(file.id) && !reading.includes(file.id),
  );
  const [picked, setPicked] = useState(null); // null: the newest unread file
  const ticked = picked ?? new Set(unread.length ? [unread[unread.length - 1].id] : []);
  const toRead = unread.filter((file) => ticked.has(file.id));
  const open = Number(params.get('doc')) || null;
  const choices = meta.document_kinds.filter((kind) => kind.file_as);
  const busy = attach.busy || update.isPending;

  function toggle(id) {
    const next = new Set(ticked);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setPicked(next);
  }

  async function refile(file, kind) {
    try {
      await update.mutateAsync({ documentId: file.id, changes: { kind } });
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <>
      <FileAsList
        pending={attach.pending}
        meta={meta}
        upload={attach.uploader}
        onChange={attach.setPending}
        onDone={(_count, filed) => attach.filed(filed)}
      />
      {live.length > 0 && (
        <div className="bnf-scanchat-rows">
          {live.map((file) => {
            const read = readIds.includes(file.id);
            const reads = readable.includes(file.kind);
            const kinds = choices.some((kind) => kind.key === file.kind)
              ? choices
              : [...choices, meta.document_kinds.find((kind) => kind.key === file.kind) || { key: file.kind, label: file.kind }];
            return (
              <div
                key={file.id}
                className={`bnf-scanchat-row${read ? ' bnf-scanchat-row-scanned' : ''}${open === file.id ? ' bnf-scanchat-row-open' : ''}`}
              >
                <label className="bnf-scanchat-tick" title="Include in the next read">
                  <input
                    type="checkbox"
                    aria-label={`Read ${file.display_name}`}
                    checked={reads && !read && ticked.has(file.id)}
                    disabled={!reads || read || busy}
                    onChange={() => toggle(file.id)}
                  />
                </label>
                <div className="bnf-scanchat-rowlines">
                  <div className="bnf-scanchat-rowtop">
                    <button
                      type="button"
                      className="bnf-scanchat-rowname"
                      title={`${file.display_name} — open it on Documents`}
                      onClick={() => navigate(`/deals/${dealId}/documents?doc=${file.id}`)}
                    >
                      📄 {file.display_name}
                    </button>
                    {open === file.id && <span className="bnf-scanchat-open-tag">👁 open</span>}
                  </div>
                  <div className="bnf-scanchat-rowbot">
                    <select
                      className="bnf-scanchat-doctype"
                      value={file.kind}
                      disabled={busy || file.protected}
                      aria-label={`File ${file.display_name} as`}
                      title="What kind of file is this? Claude reads it by this"
                      onChange={(event) => refile(file, event.target.value)}
                    >
                      {kinds.map((kind) => (
                        <option key={kind.key} value={kind.key}>
                          {kind.label}
                        </option>
                      ))}
                    </select>
                    {read && <span className="bnf-scanchat-doc-tag">scanned</span>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {unread.length > 0 && (
        <div className="bnf-scanchat-runrow">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={busy || !toRead.length}
            onClick={() => attach.read(toRead)}
          >
            {readButton(toRead.length)}
          </button>
          <span className="bnf-scanchat-runhint">
            {toRead.length ? 'Claude reads them into the grids — give it a minute per file.' : 'Tick a file above to read it.'}
          </span>
        </div>
      )}
    </>
  );
}
