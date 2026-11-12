import { Link } from 'react-router';
import RefreshChip from '../../ui/RefreshChip';
import { ARCHIVED_LINK_TIP } from '../ArchivedPage/archiveCopy';
import { VIEWS } from './homeParams';

/**
 * The view pill (`bnf-viewtab`, A9, I87, CL10) with the shown list's Refreshing… chip beside it, then the Archived
 * link (a link, not a view; CasesDashboard.jsx at 891f1b3). The Work queue pill waits for slice 61.
 */
export default function ViewBar({ view, onView, refreshing, failed, onRetry }) {
  return (
    <div className="bnf-home-viewbar">
      <div className="bnf-viewtabs" role="tablist" aria-label="Benefits views">
        {VIEWS.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={view === item.key}
            className={view === item.key ? 'bnf-viewtab bnf-viewtab-on' : 'bnf-viewtab'}
            onClick={() => onView(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <RefreshChip label="Refreshing…" loading={refreshing} error={failed} onRetry={onRetry} />
      <Link className="bnf-archived-link" to="/archived" title={ARCHIVED_LINK_TIP}>
        Archived
      </Link>
    </div>
  );
}
