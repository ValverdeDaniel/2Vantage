import { useId, useState } from 'react';
import { useUpdateDeal } from '../../api/deals';
import { lineLabel } from '../../api/meta';
import ConfirmDialog from '../../ui/ConfirmDialog';
import MultiSelect from '../../ui/MultiSelect';
import SaveStatus from '../../ui/SaveStatus';
import styles from './HeaderFields.module.css';

/**
 * Lines: [Medical ✕] [Dental ✕] [+ Line] — the lines to quote, in meta order (plan.md §8.4). Adding saves at once;
 * removing asks first, because the line's plans disappear from view (they are kept).
 */
export default function LinesPicker({ deal, meta }) {
  const labelId = useId();
  const update = useUpdateDeal(deal.id);
  const [removing, setRemoving] = useState(null);
  const options = meta.lines.map((line) => ({ value: line.key, label: line.label }));

  function confirmRemove() {
    update.mutate({ requested_lines: deal.requested_lines.filter((key) => key !== removing) });
    setRemoving(null);
  }

  return (
    <div className={styles.linesRow} role="group" aria-labelledby={labelId}>
      <span id={labelId} className={styles.label}>
        Lines:
      </span>
      <MultiSelect
        options={options}
        value={deal.requested_lines}
        onChange={(next) => update.mutate({ requested_lines: next })}
        onRemove={setRemoving}
        addLabel="+ Line"
        label="Lines to quote"
        placeholder="Search lines…"
        emptyText="None yet."
      />
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
