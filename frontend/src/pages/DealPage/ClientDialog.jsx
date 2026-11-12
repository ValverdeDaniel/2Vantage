import { useId, useState } from 'react';
import { useDealClient, useSetClientStatus, useUpdateClient } from '../../api/deals';
import { relationshipLabel } from '../../api/meta';
import { statusBadgeClass } from '../../lib/dealLook';
import { errorText, fieldErrors, formErrorText } from '../../lib/errors';
import { formatDate } from '../../lib/format';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import TextInput from '../../ui/TextInput';

// Each move the server offers (plan.md §5.1): allowed ones act at once; refused ones are greyed, with their sentence
// as the tooltip. A move that is refused after all (a 409) shows its sentence below.
function StatusMoves({ deal, meta }) {
  const client = useDealClient(deal);
  const setStatus = useSetClientStatus(deal);
  const shown = client.data || deal.client; // the header's copy until the full client arrives
  const moves = client.data?.moves || [];
  const titleId = useId();

  return (
    <div role="group" aria-labelledby={titleId} className="form-group">
      <label id={titleId}>Status</label>
      <div className="bnf-ov-chips">
        <span className={statusBadgeClass(shown.relationship)}>{relationshipLabel(meta, shown.relationship)}</span>
        {shown.client_since && <span className="bb-drop-meta">since {formatDate(shown.client_since)}</span>}
      </div>
      {client.isError && (
        <div role="alert" className="error-message bb-mt">
          {errorText(client.error)}
        </div>
      )}
      <div className="bnf-ov-chips">
        {moves.map((move) => (
          // A disabled button takes no pointer events, so the tooltip comes from the span around it.
          <span key={move.to} title={move.allowed ? undefined : move.sentence}>
            <Button
              size="sm"
              disabled={!move.allowed}
              busy={setStatus.isPending && setStatus.variables === move.to}
              aria-label={move.allowed ? undefined : `${move.label} — ${move.sentence}`}
              onClick={() => setStatus.mutate(move.to)}
            >
              {move.label}
            </Button>
          </span>
        ))}
      </div>
      {setStatus.isError && (
        <div role="alert" className="error-message bb-mt">
          {errorText(setStatus.error)}
        </div>
      )}
    </div>
  );
}

/** Edit the client's name (PATCH clients/{id}/) and move its status (POST clients/{id}/status/). */
export default function ClientDialog({ deal, meta, onClose }) {
  const update = useUpdateClient(deal);
  const [name, setName] = useState(deal.client.name);
  const [missing, setMissing] = useState(false);
  const errors = fieldErrors(update.error);
  const formError = formErrorText(update.error, ['name']);

  function onSubmit(event) {
    event.preventDefault();
    if (!name.trim()) {
      setMissing(true);
      return;
    }
    update.mutate({ name: name.trim() }, { onSuccess: onClose });
  }

  return (
    <Modal
      open
      onClose={onClose}
      onSubmit={onSubmit}
      title="Edit client"
      size="sm"
      footer={
        <>
          <Button size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" type="submit" variant="primary" busy={update.isPending}>
            Save
          </Button>
        </>
      }
    >
      <Field label="Client name" required error={missing && !name.trim() ? 'Enter the client name.' : errors.name}>
        <TextInput value={name} maxLength={200} onChange={(event) => setName(event.target.value)} />
      </Field>
      <StatusMoves deal={deal} meta={meta} />
      {formError && (
        <div role="alert" className="error-message">
          {formError}
        </div>
      )}
    </Modal>
  );
}
