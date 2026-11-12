import BuilderCard from '../../shared/BuilderCard';
import SummaryPreview from './SummaryPreview';
import { moved } from './builderModel';
import { blockScope, everyBlock, pinnedBlock, summaryBlocks, summaryWords, takesPin, toggledBlock } from './dealCardsModel';

/*
 * Executive summary (plan.md §8.14; J64–J66; the old summary card of ProposalBuilder.jsx at 891f1b3, same words and
 * classes): what are my options, what am I looking at, what should I do — picked, not written. Show it; the figures
 * the catalogue offers (13 per line, 8 for the whole deal), all / clear; the picked ones in order with ▲ ▼ and a line
 * pin for a per-line figure; and the live preview with the reason a figure is unavailable. While nothing is picked the
 * deal's standard set shows, and every edit builds on it, so unticking one standard figure keeps the others. Each edit
 * writes `summary.blocks` or `summary.on` (J20). The catalogue is `/api/meta/` proposal.summary; every figure and
 * reason is the server's (`summary.blocks`). `templates` is the summary's TEMPLATE bar (J68; slice 34).
 */
export default function SummaryCard({ summary, lines, lineLabel, newGroup, meta, card, busy, onSet, templates = null }) {
  const catalog = meta.summary.blocks;
  const blocks = summaryBlocks(summary);
  const chosen = new Set(blocks.map((block) => block.key));
  const entryOf = (key) => catalog.find((entry) => entry.key === key);
  const write = (next) => onSet('summary.blocks', next);
  return (
    <BuilderCard guide="build-summary" title="Executive summary" summary={summaryWords(summary)} card={card}>
      <div className="bnf-build-head">
        <div className="bb-panel-sub">
          What are my options, what am I looking at, what should I do — picked, not written. Every figure is calculated
          from this deal.
        </div>
        <label className="bnf-filter-check">
          <input type="checkbox" disabled={busy} checked={summary.on} onChange={() => onSet('summary.on', !summary.on)} />
          Show it
        </label>
      </div>
      {newGroup && (
        <div className="bb-drop-meta bnf-build-newhint">
          New group — blocks that compare against a current plan will refuse with a reason; the preview below shows why.
          The standard set for a new group leads with first-year cost and what is being proposed.
        </div>
      )}
      {templates}
      <div className="bnf-build-rowshead">
        <span className="bnf-build-rowgroup-title">Figures</span>
        <span className="bnf-build-selectall">
          <button
            type="button"
            disabled={busy || blocks.length === catalog.length}
            title="Pick every figure the catalog offers"
            onClick={() => write(everyBlock(blocks, catalog))}
          >
            all
          </button>
          <button
            type="button"
            disabled={busy || summary.picked.length === 0}
            title="Back to the standard set — use 'Show it' to drop the summary entirely"
            onClick={() => write([])}
          >
            clear
          </button>
        </span>
      </div>
      <div className="bnf-build-blocks">
        {catalog.map((entry) => (
          <label key={entry.key} className="bnf-filter-check">
            <input
              type="checkbox"
              disabled={busy}
              checked={chosen.has(entry.key)}
              onChange={() => write(toggledBlock(blocks, entry.key))}
            />
            {entry.label}
            <span className="bb-drop-meta">{blockScope(entry, lineLabel)}</span>
          </label>
        ))}
        {summary.picked.length === 0 && (
          <div className="bb-drop-meta">
            Nothing picked yet — the ticked figures are the standard set this deal shows. Tick or untick one to make the
            set yours.
          </div>
        )}
      </div>
      {blocks.length > 0 && (
        <div className="bnf-build-chosen">
          <div className="bnf-build-rowgroup-title">In this order</div>
          {blocks.map((spec, i) => (
            <div key={`${spec.key}-${i}`} className="bnf-build-chosen-row">
              <button
                type="button"
                className="bnf-build-order-btn"
                disabled={busy || i === 0}
                title="Move up"
                onClick={() => write(moved(blocks, i, -1))}
              >
                ▲
              </button>
              <button
                type="button"
                className="bnf-build-order-btn"
                disabled={busy || i === blocks.length - 1}
                title="Move down"
                onClick={() => write(moved(blocks, i, 1))}
              >
                ▼
              </button>
              <span className="bnf-build-chosen-label">{entryOf(spec.key)?.label ?? spec.key}</span>
              {takesPin(entryOf(spec.key)) && (
                <select
                  className="filter-select bnf-build-block-pin"
                  disabled={busy}
                  value={spec.line || ''}
                  title="Which line this figure is computed for"
                  onChange={(event) => write(pinnedBlock(blocks, spec.key, event.target.value))}
                >
                  <option value="">Every line</option>
                  {lines.map((line) => (
                    <option key={line.line} value={line.line}>
                      {line.label} only
                    </option>
                  ))}
                </select>
              )}
            </div>
          ))}
        </div>
      )}
      <SummaryPreview blocks={summary.blocks} />
    </BuilderCard>
  );
}
