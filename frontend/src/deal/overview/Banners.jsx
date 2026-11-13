import { useState } from 'react';
import { useArchiveClient } from '../../api/clients';
import { useMarkLost, useReopenDeal } from '../../api/deals';
import { errorText } from '../../lib/errors';
import { formatDate, personName } from '../../lib/format';
import { ARCHIVE_CLIENT_TIP, RESTORE_TIP } from '../../pages/ArchivedPage/archiveCopy';

// The Overview's deal actions under its title (M1–M7, M103; old Vantage 891f1b3 `CaseOverviewTab.jsx`), moved here
// from the header strip in slice 62 (M112: the strip keeps only the stage). Each writes through deals' doors (Mark
// lost, Reopen, the client's archive) and reads the deal header every tab shares. What is archived is the client, and
// its one deal with it (OQ46), so the words name the client.

/** The inline lost row (M2): "Why did we lose it? (optional)", Enter or Confirm lost, Cancel; the server's sentence. */
export function LostRow({ deal, onDone }) {
  const markLost = useMarkLost(deal.id);
  const [reason, setReason] = useState('');
  const confirm = () => markLost.mutate(reason.trim(), { onSuccess: onDone });
  return (
    <div className="bnf-lost-banner bnf-lost-confirm" role="group" aria-label="Mark this deal lost">
      <input
        className="bnf-intake-input"
        aria-label="Why did we lose it? (optional)"
        placeholder="Why did we lose it? (optional)"
        maxLength={300}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') confirm();
          if (event.key === 'Escape') onDone();
        }}
        autoFocus
      />
      <button type="button" className="btn btn-primary btn-sm" disabled={markLost.isPending} onClick={confirm}>
        Confirm lost
      </button>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onDone}>
        Cancel
      </button>
      {markLost.isError && (
        <span role="alert" className="bb-rose">
          {errorText(markLost.error)}
        </span>
      )}
    </div>
  );
}

/** "Archive <client>? …" with Archive and Cancel (M6). */
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

/** "🗄 Archived <date> by <name> — off every list. Nothing was deleted." with Restore (M7). */
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

/** "✕ Lost <date> — <reason | no reason recorded>" with Reopen deal (M4). A lost deal stays editable. */
export function LostBanner({ deal }) {
  const reopen = useReopenDeal(deal.id);
  return (
    <div className="bnf-lost-banner" role="status">
      <span>
        ✕ <strong>Lost</strong>
        {deal.lost_at ? ` ${formatDate(deal.lost_at)}` : ''}
        {' — '}
        {deal.lost_reason || 'no reason recorded'}
        {reopen.isError && <span role="alert"> · {errorText(reopen.error)}</span>}
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={reopen.isPending}
        onClick={() => reopen.mutate()}
      >
        Reopen deal
      </button>
    </div>
  );
}
