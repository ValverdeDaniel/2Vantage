import { useState } from 'react';
import { useAgendaWrites } from '../../api/agenda';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * What each Agenda button does (I15–I24, I31–I33), each one request (I.5 bug 8), with the old toasts ("Held back until
 * then", "Marked done", "Task done"…) and the API's own sentence on a refusal (I8). Done anyway and Delete ask first
 * (I19, OQ93): `confirm` holds the open question for the tab's ConfirmDialog. `form` is the one row form open
 * ({rowId, type: later | follow_up | edit}).
 */
export default function useAgendaActions(dealId) {
  const toast = useToast();
  const writes = useAgendaWrites(dealId);
  const [busy, setBusy] = useState(null);
  const [form, setForm] = useState(null);
  const [confirm, setConfirm] = useState(null);

  async function run(rowId, call, said) {
    setBusy(rowId);
    try {
      const answer = await call();
      setForm(null);
      if (said) toast.success(said);
      return answer ?? true;
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not save that.' }));
      return null;
    } finally {
      setBusy(null);
    }
  }

  const toggle = (row, type) => setForm(form?.rowId === row.id && form.type === type ? null : { rowId: row.id, type });

  function act(row, key) {
    const task = { taskId: row.task_id };
    switch (key) {
      case 'later':
      case 'follow_up':
      case 'edit':
        return toggle(row, key);
      case 'bring_back':
        return run(row.id, () => writes.clearMark.mutateAsync({ stepKey: row.key }), 'Back on the Agenda');
      case 'undo':
        return run(row.id, () => writes.clearMark.mutateAsync({ stepKey: row.key }), 'Step reopened');
      case 'done_anyway':
        return setConfirm({
          title: `Count “${row.label}” done anyway?`,
          message: 'It comes back if the step changes.',
          label: 'Done anyway',
          go: () => run(row.id, () => writes.doneAnyway.mutateAsync({ stepKey: row.key }), 'Marked done'),
        });
      case 'tick':
        return run(row.id, () => writes.updateTask.mutateAsync({ ...task, done: true }), 'Task done');
      case 'reopen':
        return run(row.id, () => writes.updateTask.mutateAsync({ ...task, done: false }), 'Task reopened');
      case 'delete':
        return setConfirm({
          title: 'Delete this task?',
          message: 'It leaves the Agenda. The activity log can bring it back.',
          label: 'Delete',
          danger: true,
          go: () => run(row.id, () => writes.deleteTask.mutateAsync(task), 'Task deleted'),
        });
      default:
        return null;
    }
  }

  const later = (row, until, note) =>
    row.kind === 'task'
      ? run(row.id, () => writes.updateTask.mutateAsync({ taskId: row.task_id, due: until, move_note: note }), 'Task moved')
      : run(row.id, () => writes.later.mutateAsync({ stepKey: row.key, until, note }), 'Held back until then');
  const followUp = (row, body, kind) =>
    run(row.id, () => writes.followUp.mutateAsync({ stepKey: row.key, kind, body }), 'Follow-up logged');
  const editTask = (row, changes) =>
    run(row.id, () => writes.updateTask.mutateAsync({ taskId: row.task_id, ...changes }), 'Task saved');
  const addTask = (body) => run('add', () => writes.addTask.mutateAsync(body), 'Task added');

  return {
    busy,
    form,
    setForm,
    act,
    later,
    followUp,
    editTask,
    addTask,
    confirm,
    closeConfirm: () => setConfirm(null),
  };
}
