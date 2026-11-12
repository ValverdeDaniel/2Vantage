import { useUpdateDocument } from '../../api/documents';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { fileFacts, factsTitle, kindLabel, readButton, readsInto } from './drawerWords';

/*
 * The file chips (plan.md §8.17; D13, D14; the old ScanChat's `bnf-scanchat-doc` pills): on a tab whose files Claude
 * reads, the deal's files of those kinds, each with what it is filed as, what is in it (its role: current plans, a
 * renewal or alternates, which the reader is told; E13), what Claude is sent of it (pages, member pages left out,
 * image pages) and "scanned" once a read has read it — for everyone. Files no read has read, and none is reading now,
 * can be read from here.
 */
export default function FileChips({ dealId, files, kinds, meta, readIds, reading, busy, onRead }) {
  const toast = useToast();
  const update = useUpdateDocument(dealId);
  const shown = files.filter((file) => kinds.includes(file.kind) && !file.archived_at);
  if (!shown.length) return null;
  const unread = shown.filter((file) => !readIds.includes(file.id) && !reading.includes(file.id));
  const roles = meta.document_roles || [];

  async function change(file, changes) {
    try {
      await update.mutateAsync({ documentId: file.id, changes });
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <>
      <div className="bnf-scanchat-docs">
        {shown.map((file) => {
          const read = readIds.includes(file.id);
          const asksRole = meta.document_kinds.find((kind) => kind.key === file.kind)?.asks_role;
          const facts = fileFacts(file, readsInto(meta, file.kind).members);
          return (
            <span key={file.id} className={`bnf-scanchat-doc ${read ? 'scanned' : ''}`} data-file-chip={file.id}>
              📄 {file.display_name}
              <span className="bnf-scanchat-doc-facts" title={factsTitle(file, readsInto(meta, file.kind).members)}>
                {' · '}
                <select
                  className="bnf-scanchat-doc-kind"
                  value={file.kind}
                  disabled={busy || update.isPending}
                  aria-label={`What ${file.display_name} is`}
                  title="What this file is: Claude reads it as this"
                  onChange={(event) => change(file, { kind: event.target.value })}
                >
                  {kinds.map((key) => (
                    <option key={key} value={key}>
                      {kindLabel(meta, key)}
                    </option>
                  ))}
                </select>
                {asksRole && (
                  <select
                    className="bnf-scanchat-doc-kind"
                    value={file.role || ''}
                    disabled={busy || update.isPending}
                    aria-label={`What is in ${file.display_name}`}
                    title="What is in it: current plans, a renewal of them, or alternate quotes. Claude is told."
                    onChange={(event) => change(file, { role: event.target.value })}
                  >
                    <option value="">What is in it?</option>
                    {roles.map((role) => (
                      <option key={role.key} value={role.key}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                )}
                {facts ? ` · ${facts}` : ''}
              </span>
              {read && <span className="bnf-scanchat-doc-tag">scanned</span>}
            </span>
          );
        })}
      </div>
      {unread.length > 0 && (
        <div className="bnf-scanchat-runrow">
          <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={() => onRead(unread)}>
            {readButton(unread.length)}
          </button>
          <span className="bnf-scanchat-runhint">
            Claude reads them into {readsInto(meta, shown[0].kind).into} — give it a minute per file.
          </span>
        </div>
      )}
    </>
  );
}
