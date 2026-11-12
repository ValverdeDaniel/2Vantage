import { useState } from 'react';
import { useArchiveClient } from '../../api/clients';
import ConfirmDialog from '../../ui/ConfirmDialog';
import { useToast } from '../../ui/useToast';
import { ARCHIVE_CLIENT_TIP } from '../ArchivedPage/archiveCopy';

// Archive from the home tables (I126; HomeCells.jsx and ClientsDashboard.jsx at 891f1b3): the header's ⓘ says what
// archive does; each row ends in a small Archive button that asks first. A client and its one deal leave together
// (OQ46), so every row offers it, a sold deal's too.

/** The Archive column's header: the ⓘ with what archive does. */
export function ArchiveTh() {
  return (
    <div className="bnf-th-archive">
      <span className="bnf-archive-hint" title={ARCHIVE_CLIENT_TIP} aria-label={ARCHIVE_CLIENT_TIP}>
        ⓘ
      </span>
    </div>
  );
}

/** A row's Archive button and its confirmation. Clicks inside never reach the row, which opens the deal. */
export function ArchiveCell({ row }) {
  const [asking, setAsking] = useState(false);
  const archive = useArchiveClient();
  const toast = useToast();

  function confirm() {
    archive.mutate(
      { clientId: row.id, archived: true, dealId: row.deal?.id },
      {
        onSuccess: () => {
          setAsking(false);
          toast.success(`Archived ${row.name}. Restore it from Archived.`);
        },
      },
    );
  }

  return (
    <div className="bnf-th-archive" onClick={(event) => event.stopPropagation()}>
      <button
        type="button"
        className="bnf-row-archive"
        title={ARCHIVE_CLIENT_TIP}
        aria-label={`Archive ${row.name}`}
        onClick={() => {
          archive.reset();
          setAsking(true);
        }}
      >
        Archive
      </button>
      <ConfirmDialog
        open={asking}
        title={`Archive ${row.name}?`}
        message={ARCHIVE_CLIENT_TIP}
        confirmLabel="Archive"
        busy={archive.isPending}
        error={archive.error}
        onConfirm={confirm}
        onCancel={() => setAsking(false)}
      />
    </div>
  );
}
