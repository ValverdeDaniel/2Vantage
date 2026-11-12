import { formatMoney } from '../../../lib/format';
import { money, planWords } from './stopLossModel';

/*
 * ② The verdict (plan.md §8.14; F100, F101; the old StopLossAnalysis.jsx at 891f1b3): the options ranked lowest first
 * on the chosen key (the server's ranking), ★ to shortlist, the maximum annual liability with its change against the
 * one in-force contract, then the in-force contracts as the baseline. The punchline compares the lowest premium with
 * the lowest liability, whatever the rank key (bug 20 fixed on the server).
 */
function VersusCurrent({ value }) {
  if (value == null) return <span className="bnf-delta-base">no comparison</span>;
  if (value === 0) return <span className="bnf-delta">Same as current</span>;
  return (
    <span className={`bnf-delta ${value > 0 ? 'bnf-delta-pos' : 'bnf-delta-neg'}`}>
      {formatMoney(value, { signed: true })} vs current
    </span>
  );
}

function Name({ column }) {
  return (
    <span className="bnf-sl-rank-name">
      <b>{column.carrier || '—'}</b>
      <span>{column.name}</span>
    </span>
  );
}

function Figures({ figures }) {
  return (
    <div className="bnf-sl-rank-figs">
      <span>
        premium <b className="bb-mono">{money(figures.annual_premium)}</b>
      </span>
      <span>
        lasers <b className="bb-mono">{money(figures.laser_liability)}</b>
      </span>
    </div>
  );
}

export default function VerdictCards({ options, currents, single, rankLabel, punchline, onStar }) {
  if (!options.length) return null;
  return (
    <div>
      <div className="bnf-sl-section-title">Verdict — ranked on {rankLabel.toLowerCase()} (lowest wins)</div>
      <div className="bnf-sl-ranks" role="list" aria-label="Verdict">
        {options.map((column, i) => (
          <div
            key={column.id}
            className={`bnf-sl-rank ${i === 0 ? 'bnf-sl-rank-best' : ''}`}
            role="listitem"
            aria-label={`Rank ${i + 1}: ${planWords(column)}`}
          >
            <div className="bnf-sl-rank-top">
              <span className="bnf-sl-rank-badge">{i + 1}</span>
              <button
                type="button"
                className={`bnf-star-btn ${column.starred ? 'active' : ''}`}
                title={column.starred ? 'Remove from shortlist' : 'Add to shortlist'}
                aria-pressed={column.starred}
                onClick={() => onStar(column)}
              >
                {column.starred ? '★' : '☆'}
              </button>
              <Name column={column} />
            </div>
            <div className="bnf-sl-rank-mal" aria-label="Maximum annual liability">
              {money(column.figures.max_annual_liability)}
              {column.what_if && <span className="bnf-flag-chip">what-if</span>}
            </div>
            <div className="bnf-sl-rank-vs">
              <VersusCurrent value={column.vs?.max_annual_liability ?? null} />
            </div>
            <Figures figures={column.figures} />
          </div>
        ))}
        {currents.map((column) => (
          <div
            key={column.id}
            className="bnf-sl-rank bnf-sl-rank-base"
            role="listitem"
            aria-label={`In force: ${planWords(column)}`}
          >
            <div className="bnf-sl-rank-top">
              <span className="bnf-plan-chip bnf-chip-current">CURRENT</span>
              <Name column={column} />
            </div>
            <div className="bnf-sl-rank-mal" aria-label="Maximum annual liability">
              {money(column.figures.max_annual_liability)}
              {column.what_if && <span className="bnf-flag-chip">what-if</span>}
            </div>
            <div className="bnf-sl-rank-vs">
              <span className="bnf-delta-base">{single ? 'baseline' : 'in force'}</span>
            </div>
            <Figures figures={column.figures} />
          </div>
        ))}
      </div>
      {punchline && (
        <div className="bnf-sl-punchline">
          The lowest premium on this page is <b>{punchline.carrier}</b> — and it is not the lowest liability. That flip
          is the whole analysis.
        </div>
      )}
    </div>
  );
}
