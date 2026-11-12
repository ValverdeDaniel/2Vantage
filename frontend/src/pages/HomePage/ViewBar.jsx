import RefreshChip from '../../ui/RefreshChip';
import { VIEWS } from './homeParams';

/**
 * The view pill (`bnf-viewtab`, A9, I87, CL10) with the shown list's Refreshing… chip beside it. The Work queue pill
 * waits for slice 61 and the Archived link for slice 38.
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
    </div>
  );
}
