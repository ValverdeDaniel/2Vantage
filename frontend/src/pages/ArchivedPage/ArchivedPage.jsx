import { useEffect } from 'react';
import { Link } from 'react-router';
import { useArchiveClient, useArchived } from '../../api/clients';
import { relationshipLabel, stageLabel, useMeta } from '../../api/meta';
import { stagePillClass, statusBadgeClass } from '../../lib/dealLook';
import { errorText } from '../../lib/errors';
import { formatDate, personName } from '../../lib/format';
import { useToast } from '../../ui/useToast';
import { ARCHIVED_LINK_TIP, RESTORE_TIP } from './archiveCopy';

function stampLine(archived) {
  if (!archived) return '—';
  return `${formatDate(archived.at)}${archived.by ? ` · ${personName(archived.by)}` : ''}`;
}

/**
 * Benefits ▸ Archived (`/archived`; plan.md §8.3; A13, M105; ArchivedPage.jsx at 891f1b3): every archived client with
 * its status and its deal's stage, each with Restore. Archive is a visibility flag, never a delete, so Restore puts a
 * client back exactly as it was. A client and its one deal are archived together (OQ46), so the old page's second
 * table, deals archived on their own, is gone.
 */
export default function ArchivedPage() {
  const archived = useArchived();
  const meta = useMeta();
  const restore = useArchiveClient();
  const toast = useToast();
  const rows = archived.data || [];

  useEffect(() => {
    document.title = 'Archived — 2Vantage';
  }, []);

  function onRestore(row) {
    restore.mutate(
      { clientId: row.id, archived: false, dealId: row.deal?.id },
      {
        onSuccess: () => toast.success(`Restored ${row.name}`),
        onError: (error) => toast.error(errorText(error, { fallback: 'Could not restore that.' })),
      },
    );
  }

  const failed = archived.isError || meta.isError;
  return (
    <div className="bb-dash bnf-archived-page">
      <div className="bnf-benefits-topbar">
        <div className="bb-eyebrow">
          <Link to="/">Benefits</Link> ▸ Archived
        </div>
      </div>
      <div className="bb-dash-header">
        <div>
          <div className="bb-title" role="heading" aria-level={1}>
            Archived
          </div>
          <div className="bb-subtitle">{ARCHIVED_LINK_TIP}</div>
        </div>
      </div>

      {failed && (
        <div className="empty-state" role="alert">
          Couldn&apos;t load the archived list.{' '}
          <button
            type="button"
            className="bnf-archived-link"
            onClick={() => (archived.isError ? archived.refetch() : meta.refetch())}
          >
            Try again
          </button>
        </div>
      )}
      {!failed && (archived.isPending || meta.isPending) && <div className="loading">Loading...</div>}

      {archived.data && meta.data && (
        <div className="bnf-archived-section">
          <div className="bnf-archived-title">Clients ({rows.length})</div>
          {rows.length === 0 ? (
            <div className="empty-state">No archived clients.</div>
          ) : (
            <table className="bnf-archived-table">
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Status</th>
                  <th>Archived</th>
                  <th>Stage</th>
                  <th aria-label="Restore" />
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.deal ? <Link to={`/deals/${row.deal.id}`}>{row.name}</Link> : row.name}</td>
                    <td>
                      <span className={statusBadgeClass(row.relationship)}>
                        {relationshipLabel(meta.data, row.relationship)}
                      </span>
                    </td>
                    <td className="bb-account-sub">{stampLine(row.archived)}</td>
                    <td>
                      {row.deal ? (
                        <span className={stagePillClass(row.deal.stage)}>{stageLabel(meta.data, row.deal.stage)}</span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="bnf-archived-act">
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        title={RESTORE_TIP}
                        aria-label={`Restore ${row.name}`}
                        disabled={restore.isPending && restore.variables?.clientId === row.id}
                        onClick={() => onRestore(row)}
                      >
                        Restore
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
