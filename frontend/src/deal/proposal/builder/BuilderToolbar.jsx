import { useParams } from 'react-router';
import { useDeal } from '../../../api/deals';
import { RENEWAL } from '../../../api/meta';
import cx from '../../../ui/cx';

const LEVELS = { stop: 'Stops', warn: 'Check', info: 'Note' };

/*
 * The builder's toolbar and its Before-you-export list (plan.md §8.14; J18, J23, J27, J28; the old ProposalBuilder.jsx
 * toolbar at 891f1b3): "✓ n of N completed" with Expand/Collapse all, "⚠ n to check" opening the checks (Stops first,
 * each with Fix ▸), "Open proposal ▸", and the readiness banner — what Issue would say, before the click. The checks
 * and the sentence are the server's (proposals/checks.py, ready.py). The three file buttons arrive with the files
 * (J24; slices 27–31); "Open proposal ▸" opens the Export viewer once it exists (J27; slice 28). RENEWAL leads the
 * toolbar on a deal opened for an Existing client (J22; slice 38): the header's `deal_type`, read from the deal page's
 * cached header (the builder lives only there), never the client's status.
 */
export default function BuilderToolbar({ progress, allOpen, onAllOpen, checks, showChecks, onShowChecks, ready, onFix }) {
  const { dealId } = useParams();
  const renewal = useDeal(dealId).data?.deal_type === RENEWAL;
  return (
    <>
      <div className="bnf-build-toolbar" data-guide="build-deliver">
        {renewal && (
          <span
            className="bnf-plan-chip bnf-chip-renewal"
            title="This deal renews an existing client — the current plans are last year's sold plans"
          >
            RENEWAL
          </span>
        )}
        <span
          className={cx('bnf-build-progress', progress.done === progress.total && 'bnf-build-progress-done')}
          title="The deal-wide cards plus this line's cards; other lines keep their own marks"
        >
          ✓ {progress.done} of {progress.total} completed
        </span>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => onAllOpen(!allOpen)}>
          {allOpen ? 'Collapse all' : 'Expand all'}
        </button>
        <span className="bnf-build-toolbar-spacer" />
        <button
          type="button"
          className={cx('btn btn-secondary btn-sm bnf-build-checks-btn', checks.length && 'bnf-build-checks-btn-open')}
          aria-expanded={showChecks}
          title={checks.length ? 'What would print wrong in the client documents' : 'Nothing in the client documents looks wrong'}
          onClick={() => onShowChecks(!showChecks)}
        >
          {checks.length ? `⚠ ${checks.length} to check` : '✓ Nothing to fix'}
        </button>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled
          title="Opens the Export viewer, which arrives with the client files"
        >
          Open proposal ▸
        </button>
      </div>
      {ready.sentence && (
        <div className="bnf-build-ready" role="status">
          {ready.sentence}
        </div>
      )}
      {showChecks && checks.length > 0 && (
        <div className="bnf-build-checks" role="region" aria-label="Before you export">
          <div className="bnf-build-checks-head">
            <b>Before you export</b>
            <span className="bb-drop-meta">
              What would print wrong in the PDF, the PowerPoint or the client spreadsheet. Fix anything marked Stops
              before a client sees it; the rest is yours to judge.
            </span>
          </div>
          <ul className="bnf-build-checks-list">
            {checks.map((item, i) => (
              <li key={`${item.code}-${item.line}-${i}`} className={`bnf-build-check bnf-build-check-${item.level}`}>
                <span className="bnf-build-check-level">{LEVELS[item.level] ?? 'Check'}</span>
                <span className="bnf-build-check-msg">{item.text}</span>
                {item.fix && (
                  <button type="button" className="bnf-override-link" onClick={() => onFix(item)}>
                    Fix ▸
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
