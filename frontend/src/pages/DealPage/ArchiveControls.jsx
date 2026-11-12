import { useArchiveClient } from '../../api/clients';
import { errorText } from '../../lib/errors';
import { formatDate, personName } from '../../lib/format';
import { ARCHIVE_CLIENT_TIP, RESTORE_TIP } from '../ArchivedPage/archiveCopy';

// The old Overview's Archive… button, its inline confirmation and the archived banner (M6, M7, M103;
// CaseOverviewTab.jsx at 891f1b3), in the header strip beside Mark as lost… until slice 62 moves both to the Overview.
// What is archived is the client, and its one deal with it (OQ46), so the words name the client.

/** "Archive… ⓘ" among the title buttons. */
export function ArchiveButton({ onClick }) {
  return (
    <span className="bnf-archive-ctl">
      <button type="button" className="btn btn-secondary btn-sm" title={ARCHIVE_CLIENT_TIP} onClick={onClick}>
        Archive…
      </button>
      <span className="bnf-archive-hint" title={ARCHIVE_CLIENT_TIP} aria-label={ARCHIVE_CLIENT_TIP}>
        ⓘ
      </span>
    </span>
  );
}

/** "Archive <client>? …" with Archive and Cancel. */
export function ArchiveConfirm({ deal, onDone }) {
  const archive = useArchiveClient();
  return (
    <div className="bnf-lost-banner bnf-lost-confirm bnf-archive-confirm" role="group" aria-label="Archive this client">
      <span className="bnf-archive-confirm-text">
        <strong>Archive {deal.client.name}?</strong> {ARCHIVE_CLIENT_TIP}
        {archive.isError && <span role="alert"> · {errorText(archive.error)}</span>}
      </span>
      <button
        type="button"
        className="btn btn-primary btn-sm"
        disabled={archive.isPending}
        onClick={() =>
          archive.mutate({ clientId: deal.client.id, archived: true, dealId: deal.id }, { onSuccess: onDone })
        }
      >
        Archive
      </button>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onDone}>
        Cancel
      </button>
    </div>
  );
}

/** "🗄 Archived <date> by <name> — off every list. Nothing was deleted." with Restore. */
export function ArchivedBanner({ deal }) {
  const restore = useArchiveClient();
  const { archived } = deal;
  return (
    <div className="bnf-lost-banner bnf-archive-banner" role="status">
      <span>
        🗄 <strong>Archived</strong>
        {archived.at ? ` ${formatDate(archived.at)}` : ''}
        {archived.by ? ` by ${personName(archived.by)}` : ''}
        {' — off every list. Nothing was deleted.'}
        {restore.isError && <span role="alert"> · {errorText(restore.error)}</span>}
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        title={RESTORE_TIP}
        disabled={restore.isPending}
        onClick={() => restore.mutate({ clientId: deal.client.id, archived: false, dealId: deal.id })}
      >
        Restore
      </button>
    </div>
  );
}
