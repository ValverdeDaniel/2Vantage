import { ARCHIVE_CLIENT_TIP } from '../../ArchivedPage/archiveCopy';

/**
 * The client Overview's title row (plan.md §8.5; CL15, CL4; old `ClientOverviewTab.jsx`'s `bnf-ov-titlerow` at
 * 891f1b3): "Overview", its subtitle, then **Convert to client** for a prospect, in Start renewal's old place (which
 * waits with renewals, H104), allowed or refused with the status door's own sentence (a lost deal), and **Archive
 * client…** ⓘ, hidden while its confirm or banner shows. Convert posts the status door (rule 6).
 */
export default function ClientTitleRow({ client, overview, writes, archiving, onArchive }) {
  const convert = overview.convert;
  const { setStatus } = writes;
  return (
    <div className="bnf-ov-titlerow">
      <div>
        <div className="bb-tab-title">Overview</div>
        <div className="bb-subtitle">Who this client is, where the year stands, and what it&apos;s worth.</div>
      </div>
      <div className="bnf-cw-titlebtns">
        {convert && (
          // A disabled button takes no pointer events, so the refusal's tooltip comes from the span around it.
          <span title={convert.allowed ? undefined : convert.sentence}>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={!convert.allowed || setStatus.isPending}
              aria-label={convert.allowed ? undefined : `Convert to client — ${convert.sentence}`}
              onClick={() => setStatus.mutate('new_client')}
            >
              Convert to client
            </button>
          </span>
        )}
        {!client.archived && !archiving && (
          <span className="bnf-archive-ctl">
            <button type="button" className="btn btn-secondary btn-sm" title={ARCHIVE_CLIENT_TIP} onClick={onArchive}>
              Archive client…
            </button>
            <span className="bnf-archive-hint" title={ARCHIVE_CLIENT_TIP} aria-label={ARCHIVE_CLIENT_TIP}>
              ⓘ
            </span>
          </span>
        )}
      </div>
    </div>
  );
}
