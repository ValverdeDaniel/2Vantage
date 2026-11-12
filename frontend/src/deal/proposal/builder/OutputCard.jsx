import BuilderCard from '../../shared/BuilderCard';
import { outputSummary } from './dealCardsModel';

/*
 * How the documents look (plan.md §8.14; J38, J39, J41; the old OutputPanel.jsx at 891f1b3, same classes): the layout
 * (a page per carrier, every option side by side, or the recommendation only, which waits for every pick), the
 * package summary, and the client spreadsheet's Compare tabs, Disclaimers tab and Compare columns. Each control writes
 * one path of `output` (J20); `output` arrives with its defaults filled in. The Format (Presentation / Classic) and the
 * share link's period wait (J36, J37, J40; OQ8); layout templates come with slice 34 (J68). Every word of a choice is
 * the server's (`/api/meta/` proposal).
 */
export default function OutputCard({ output, meta, bestOnly, card, busy, onSet }) {
  const value = (key) => output[key];
  const set = (key, next) => onSet(`output.${key}`, next);
  const comparing = value('compare_tabs');
  return (
    <BuilderCard
      guide="build-output"
      className="bnf-output"
      title="How the documents look"
      summary={outputSummary(output, meta)}
      card={card}
    >
      <div className="bnf-output-body">
        <div className="bnf-output-row">
          <span className="bnf-output-label">Layout</span>
          <div className="bnf-output-seg" role="group">
            {meta.layouts.map((layout) => {
              const waits = layout.key === 'best_only' && value('layout') !== 'best_only' ? bestOnly : null;
              return (
                <button
                  key={layout.key}
                  type="button"
                  className={`btn btn-sm ${value('layout') === layout.key ? 'btn-primary' : 'btn-secondary'}`}
                  disabled={busy || Boolean(waits)}
                  title={waits || undefined}
                  onClick={() => set('layout', layout.key)}
                >
                  {layout.label}
                </button>
              );
            })}
          </div>
        </div>
        <div className="bnf-output-row">
          <span className="bnf-output-label">Sections</span>
          <label className="bnf-output-check">
            <input
              type="checkbox"
              disabled={busy}
              checked={value('package_summary')}
              onChange={(event) => set('package_summary', event.target.checked)}
            />
            Package summary
          </label>
        </div>
        <div className="bnf-output-row">
          <span className="bnf-output-label">Spreadsheet</span>
          <label className="bnf-output-check">
            <input
              type="checkbox"
              disabled={busy}
              checked={comparing}
              onChange={(event) => set('compare_tabs', event.target.checked)}
            />
            Every quoted plan (Dynamic Compare, Composite Rates and All Plans)
          </label>
          <label className="bnf-output-check">
            <input
              type="checkbox"
              disabled={busy}
              checked={value('disclaimers')}
              onChange={(event) => set('disclaimers', event.target.checked)}
            />
            Disclaimers
          </label>
        </div>
        <div className="bnf-output-row">
          <span className="bnf-output-label">Compare</span>
          <div className="bnf-output-seg" role="group">
            {meta.compare_slots.map((slots) => (
              <button
                key={slots}
                type="button"
                className={`btn btn-sm ${value('compare_slots') === slots ? 'btn-primary' : 'btn-secondary'}`}
                disabled={busy || !comparing}
                title={comparing ? undefined : 'Turn on "Every quoted plan" to include the Dynamic Compare tab'}
                onClick={() => set('compare_slots', slots)}
              >
                {slots} columns
              </button>
            ))}
          </div>
          <span className="bnf-output-hint">side by side; the drop-down lists every quote</span>
        </div>
      </div>
    </BuilderCard>
  );
}
