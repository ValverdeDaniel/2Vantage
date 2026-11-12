import PagesView from '../pages/PagesView';
import BuilderCard from './BuilderCard';
import RecommendationWords from './RecommendationWords';
import { plansSummary } from './builderModel';

/*
 * Plans on the proposal (plan.md §8.14; J47, J49–J55; the old ProposalPlansCard.jsx at 891f1b3, D-221): the line's
 * comparison pages as the PowerPoint prints them ("What the client will see", the pages folder's PagesView), with
 * Key rows / All rows (display only: the files print every row; J16), "Our recommendation" under each page (J52),
 * ⋯ More for the name on client documents (J14), "Back to the default order" (F48, J6), the off notice and the
 * EnrollmentStrip above, and the recommendation's status and words below. A gap line reads "New coverage — options
 * only". Every write is quotes' (stars, slots, order, links, recommend) or the config's (the words).
 */
export default function PlansCard({ dealId, line, card, rowsMode, onRowsMode, notice, strip, busy, actions }) {
  const gap = line.state === 'gap';
  const rec = line.recommendation;
  return (
    <BuilderCard
      guide="build-quotes"
      title={gap ? 'New coverage — options only' : 'Plans on the proposal'}
      chips={line.chip && <span className={`bnf-state-chip bnf-state-${line.chip.tone}`}>{line.chip.text}</span>}
      summary={plansSummary(line)}
      card={card}
    >
      <div className="bnf-pg-bar">
        <div className="bnf-pg-intro">
          <div className="bnf-pg-heading">What the client will see</div>
          <div className="bb-panel-sub">
            {gap ? 'Nothing is in force today, so these are options only, with no current plan to compare against. ' : ''}
            Each block is one comparison page in the PowerPoint and PDF, columns left to right. Click a plan name to change
            it. Use the arrows to reorder.
          </div>
        </div>
        {line.pages > 0 && (
          <span className="bnf-pg-tally">
            {line.presented_ids.length} plan{line.presented_ids.length === 1 ? '' : 's'} · {line.pages} page
            {line.pages === 1 ? '' : 's'}
          </span>
        )}
        <div className="bnf-pg-rowswitch" role="group" aria-label="Rows to show">
          {[
            ['key', 'Key rows'],
            ['all', 'All rows'],
          ].map(([mode, label]) => (
            <button
              key={mode}
              type="button"
              className={rowsMode === mode ? 'is-on' : ''}
              aria-pressed={rowsMode === mode}
              onClick={() => onRowsMode(mode)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {rowsMode === 'key' && (
        <div className="bnf-pg-displaynote">
          Key rows are for display only. The PowerPoint, PDF and spreadsheet show every row of each plan.
        </div>
      )}
      {line.quotes > 1 && (
        <div className="bnf-build-selectall">
          <button
            type="button"
            disabled={busy}
            title="Put the plans back in the default order: each current plan, its renewal first, then the plans in the order they were added"
            onClick={actions.resetOrder}
          >
            Back to the default order
          </button>
        </div>
      )}
      {notice}
      {strip}
      {line.quotes === 0 && (
        <div className="bb-empty">
          No quotes on this line yet.{' '}
          <button type="button" className="bnf-override-link" onClick={actions.toQuotes}>
            Add them in the Advisor ▸
          </button>
        </div>
      )}
      <div data-guide="build-deck-order">
        <PagesView
          dealId={dealId}
          line={line.line}
          lineLabel={line.label}
          preset={rowsMode}
          recommend={{ keepable: rec.keepable, disabled: rec.sold.length > 0 }}
          withMenu
        />
      </div>
      <RecommendationWords line={line} busy={busy} onRenewals={actions.recommendAll} onReasons={actions.reasons} />
    </BuilderCard>
  );
}
