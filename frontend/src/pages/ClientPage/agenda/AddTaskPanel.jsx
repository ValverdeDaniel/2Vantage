import { useState } from 'react';
import { TaskForm, useAgendaActions } from '../../../deal/agenda';
import { pickLabel, taskTarget } from './agendaView';

/**
 * The client Agenda's "Add a task" (plan.md §8.5; CL24; old 891f1b3 `ClientAgendaTab.jsx`'s client-event panel): the
 * deal's own task form (title, date, For, Add) in the old client form's classes, which posts to the deal's tasks door,
 * so the task lands on that deal's Agenda and on the Work queue. The deal pick ("On the deal renewing …") shows only
 * with two or more deals still being worked; the old "On the client" and its categories wait with client tasks
 * (I104–I108).
 */
export default function AddTaskPanel({ clientId, panels, today, meta }) {
  const [picked, setPicked] = useState('');
  const target = taskTarget(panels, picked);
  const actions = useAgendaActions(target, { clientId });
  const pick =
    panels.length > 1 ? (
      <select value={String(target)} onChange={(event) => setPicked(event.target.value)} aria-label="On">
        {panels.map((panel) => (
          <option key={panel.deal.id} value={panel.deal.id}>
            {pickLabel(panel.deal, meta)}
          </option>
        ))}
      </select>
    ) : null;
  return (
    <div className="bb-panel">
      <div className="bb-panel-title">Add a task</div>
      <div className="bb-panel-sub">Lands on the deal&apos;s Agenda and the Work queue.</div>
      {target ? (
        <TaskForm
          today={today}
          busy={actions.busy === 'add'}
          onSave={actions.addTask}
          placeholder="Add a task… (“call HR re: census”)"
          extra={pick}
          className="bnf-event-form bnf-cw-event-form bnf-ag-addform"
        />
      ) : (
        <div className="bb-drop-meta">A task lives on a deal: this client has no deal still being worked.</div>
      )}
    </div>
  );
}
