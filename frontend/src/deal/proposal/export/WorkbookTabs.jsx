import { countWords, tabLevel } from './workbookModel';

/*
 * The spreadsheet's tabs along the bottom, as Excel shows them (plan.md §8.14; J116, J118; the old WorkbookViewer tab
 * bar at 891f1b3): a dot on each tab whose checks found something, the opening tab named in its tooltip.
 */
export default function WorkbookTabs({ tabs, current, opensOn, onPick }) {
  return (
    <div className="bnf-xw-tabs" role="tablist" aria-label="Tabs">
      {tabs.map((t) => {
        const dot = tabLevel(t.counts);
        const title = [t.title === opensOn ? 'Excel opens the file on this tab' : '', countWords(t.counts).join(' · ')]
          .filter(Boolean)
          .join('. ');
        return (
          <button
            key={t.title}
            type="button"
            role="tab"
            aria-selected={t.title === current}
            className={`bnf-xw-tab ${t.title === current ? 'bnf-xw-tab-on' : ''}`}
            onClick={() => onPick(t.title)}
            title={title || undefined}
          >
            {dot && <span className={`bnf-xv-dot bnf-xv-dot-${dot}`} aria-hidden="true" />}
            {t.title}
          </button>
        );
      })}
    </div>
  );
}
