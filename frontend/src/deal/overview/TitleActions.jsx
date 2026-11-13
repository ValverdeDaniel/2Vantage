import { LOST } from '../../api/meta';
import { ARCHIVE_CLIENT_TIP } from '../../pages/ArchivedPage/archiveCopy';

/**
 * The Overview's title row (M1; old `bnf-ov-titlerow`): "Overview", its subtitle, Mark as lost… and Archive… ⓘ. Export
 * status report waits with the report (M95; OQ8). `open` is the inline row showing ('lost' | 'archive' | null); its
 * button hides while it shows, as the old page did.
 */
export default function TitleActions({ deal, open, onOpen }) {
  const lost = deal.stage === LOST;
  return (
    <div className="bnf-ov-titlerow">
      <div>
        <div className="bb-tab-title">Overview</div>
        <div className="bb-subtitle">Who this client is, where the deal stands, and what it&apos;s worth.</div>
      </div>
      <div className="bnf-ov-titlebtns">
        {!lost && open !== 'lost' && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => onOpen('lost')}>
            Mark as lost…
          </button>
        )}
        {!deal.archived && open !== 'archive' && (
          <span className="bnf-archive-ctl">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              title={ARCHIVE_CLIENT_TIP}
              onClick={() => onOpen('archive')}
            >
              Archive…
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
