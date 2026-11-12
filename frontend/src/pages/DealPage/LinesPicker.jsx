import { useId, useState } from 'react';
import { useSetIntent } from '../../api/intake';
import { lineLabel } from '../../api/meta';
import ConfirmDialog from '../../ui/ConfirmDialog';
import Menu from '../../ui/Menu';
import SaveStatus from '../../ui/SaveStatus';

/**
 * Lines: [Medical ✕] [Dental ✕] [+ Line ▾] — the lines to quote, in meta order (plan.md §8.4; B32), on the old line
 * chips (`bnf-line-chips`, `bb-chip active`), written through intake's intent door, their one writer (B17; slice 11).
 * Adding saves at once; removing asks first, because the line stops being shopped (a line in force stays on the
 * proposal, kept as-is, until the coverage card says Leave off).
 */
export default function LinesPicker({ deal, meta }) {
  const labelId = useId();
  const update = useSetIntent(deal.id);
  const [removing, setRemoving] = useState(null);
  const chosen = meta.lines.filter((line) => deal.requested_lines.includes(line.key));
  const others = meta.lines.filter((line) => !deal.requested_lines.includes(line.key));

  function add(key) {
    update.mutate({ line: key, shop: true });
  }

  function confirmRemove() {
    update.mutate({ line: removing, shop: false });
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
        message="It stops being shopped. Plans on this line are kept."
        confirmLabel="Remove line"
        tone="danger"
        onConfirm={confirmRemove}
        onCancel={() => setRemoving(null)}
      />
    </div>
  );
}
