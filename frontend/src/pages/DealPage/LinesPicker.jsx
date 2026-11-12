import { useId, useState } from 'react';
import { useUpdateDeal } from '../../api/deals';
import { lineLabel } from '../../api/meta';
import ConfirmDialog from '../../ui/ConfirmDialog';
import Menu from '../../ui/Menu';
import SaveStatus from '../../ui/SaveStatus';

/**
 * Lines: [Medical ✕] [Dental ✕] [+ Line ▾] — the lines to quote, in meta order (plan.md §8.4; B32), on the old line
 * chips (`bnf-line-chips`, `bb-chip active`). Adding saves at once; removing asks first, because the line's plans
 * disappear from view (they are kept).
 */
export default function LinesPicker({ deal, meta }) {
  const labelId = useId();
  const update = useUpdateDeal(deal.id);
  const [removing, setRemoving] = useState(null);
  const chosen = meta.lines.filter((line) => deal.requested_lines.includes(line.key));
  const others = meta.lines.filter((line) => !deal.requested_lines.includes(line.key));

  function add(key) {
    const keys = new Set([...deal.requested_lines, key]);
    update.mutate({ requested_lines: meta.lines.map((line) => line.key).filter((k) => keys.has(k)) });
  }

  function confirmRemove() {
    update.mutate({ requested_lines: deal.requested_lines.filter((key) => key !== removing) });
    setRemoving(null);
  }

  return (
    <div className="bnf-line-chips" role="group" aria-labelledby={labelId}>
      <span id={labelId} className="bnf-line-chips-label">
        Lines
      </span>
      {chosen.map((line) => (
        <button
          key={line.key}
          type="button"
          className="bb-chip active"
          title={`Remove ${line.label}`}
          aria-label={`Remove ${line.label}`}
          onClick={() => setRemoving(line.key)}
        >
          {line.label} ✕
        </button>
      ))}
      {!chosen.length && <span className="bb-drop-meta">None yet.</span>}
      {others.length > 0 && (
        <Menu
          label="+ Line"
          buttonClassName="bb-chip"
          items={others.map((line) => ({ key: line.key, label: line.label, onSelect: () => add(line.key) }))}
        />
      )}
      <SaveStatus mutation={update} />
      <ConfirmDialog
        open={removing !== null}
        title={`Remove ${lineLabel(meta, removing)}?`}
        message="Plans on this line are kept and show again if you add the line back."
        confirmLabel="Remove line"
        tone="danger"
        onConfirm={confirmRemove}
        onCancel={() => setRemoving(null)}
      />
    </div>
  );
}
