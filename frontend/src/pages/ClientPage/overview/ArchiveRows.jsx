import { errorText } from '../../../lib/errors';
import { formatDate, personName } from '../../../lib/format';
import { ARCHIVE_CLIENT_TIP, RESTORE_TIP } from '../../ArchivedPage/archiveCopy';

// Archive client… on the client page (plan.md §8.5; CL15; M6, M7, M103; old `ClientOverviewTab.jsx` at 891f1b3): the
// inline confirm, then the banner with Restore. Both write through deals' archive door; the page and the deal refetch.

/** "Archive this client? …" with Archive client and Cancel (M6). */
export function ArchiveConfirm({ writes, onDone }) {
  const { archive } = writes;
  return (
    <div className="bnf-lost-banner bnf-lost-confirm bnf-archive-confirm" role="group" aria-label="Archive this client">
      <span className="bnf-archive-confirm-text">
        <strong>Archive this client?</strong> {ARCHIVE_CLIENT_TIP}
        {archive.isError && <span role="alert"> · {errorText(archive.error)}</span>}
      </span>
      <button
        type="button"
        className="btn btn-primary btn-sm"
        disabled={archive.isPending}
        onClick={() => archive.mutate(true, { onSuccess: onDone })}
      >
        Archive client
      </button>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onDone}>
        Cancel
      </button>
    </div>
  );
}

/** "🗄 Archived <date> by <name> — this client and its deal are off every list. Nothing was deleted." (M7) */
export function ArchivedBanner({ client, writes }) {
  const { archive } = writes;
  const { archived } = client;
  return (
    <div className="bnf-lost-banner bnf-archive-banner" role="status">
      <span>
        🗄 <strong>Archived</strong>
        {archived.at ? ` ${formatDate(archived.at)}` : ''}
        {archived.by ? ` by ${personName(archived.by)}` : ''}
        {' — this client and its deal are off every list. Nothing was deleted.'}
        {archive.isError && <span role="alert"> · {errorText(archive.error)}</span>}
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        title={RESTORE_TIP}
        disabled={archive.isPending}
        onClick={() => archive.mutate(false)}
      >
        Restore
      </button>
    </div>
  );
}
