import { useState } from 'react';
import { AgendaRow, useAgendaActions } from '../../../deal/agenda';
import { doneRows, doneWords } from './agendaView';

function DealDone({ clientId, entry, meta }) {
  const actions = useAgendaActions(entry.deal.id, { clientId });
  return entry.rows.map((row) => (
    <AgendaRow key={row.id} row={row} meta={meta} busy={actions.busy === row.id} onAction={actions.act} />
  ));
}

/**
 * The client Agenda's "Done" (plan.md §8.5; CL24; old 891f1b3 `ClientAgendaTab.jsx`'s Done panel): how many tasks were
 * ticked on the client's deals and, with Show, their rows, each with ↺ to reopen it on its deal. The old cleared
 * reminders wait with reminders (I104–I108).
 */
export default function DonePanel({ clientId, panels, meta }) {
  const [shown, setShown] = useState(false);
  const found = doneRows(panels);
  const count = found.reduce((sum, entry) => sum + entry.rows.length, 0);
  return (
    <div className="bb-panel">
      <div className="bnf-cw-agenda-head">
        <div>
          <div className="bb-panel-title">Done</div>
          <div className="bb-panel-sub">{doneWords(count)}</div>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShown((now) => !now)}>
          {shown ? 'Hide' : 'Show'}
        </button>
      </div>
      {shown && count === 0 && <div className="empty-state">Nothing marked done yet.</div>}
      {shown && found.map((entry) => <DealDone key={entry.deal.id} clientId={clientId} entry={entry} meta={meta} />)}
    </div>
  );
}
