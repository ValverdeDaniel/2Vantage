import { useQueryClient } from '@tanstack/react-query';
import { createElement, useState } from 'react';
import {
  addMember,
  censusExportPath,
  censusTemplatePath,
  clearRoster,
  getMissing,
  postCensusMarks,
  removeMember,
} from '../../api/census';
import { invalidateDeal, revertActivity } from '../../api/deals';
import { downloadFile } from '../../lib/download';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { reviewToast } from '../../valuereview/reviewWords';

/*
 * The roster's actions beside the cell writes (plan.md §7.7, §8.10; C7, C8, C24, C38; the old CensusGrid at 891f1b3):
 * ＋ Add employee and ＋ Dep (the cursor lands on the new person: a dependent's First Name), × remove, Clear roster,
 * review marks on the picked cells or every open warning (the toast offers Undo, which reverts the one `marked`
 * row), "Select all missing" (the roster's required blanks, whatever page is shown), and the two downloads. Each waits
 * for the cells still saving first, so what comes back has them. `busy` names what is in flight.
 */
export default function useRosterActions({ dealId, writes, relay, landOn, onPage, pageSize }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [busy, setBusy] = useState({});

  const refresh = () => invalidateDeal(queryClient, dealId);
  async function running(name, work) {
    setBusy((now) => ({ ...now, [name]: true }));
    try {
      return await work();
    } catch (error) {
      toast.error(errorText(error));
      return null;
    } finally {
      setBusy((now) => ({ ...now, [name]: false }));
    }
  }
  const relayed = relay ? { relay: true } : {};

  const addEmployee = () =>
    running('add', async () => {
      await writes.settle();
      const answer = await addMember(dealId, { kind: 'employee', ...relayed });
      onPage(Math.max(1, Math.ceil(answer.summary.employees / pageSize))); // a new employee sorts last
      await refresh();
      landOn(answer.member.id, null);
    });

  const addDependent = (employee, relationship) =>
    running('add', async () => {
      await writes.settle();
      const answer = await addMember(dealId, {
        kind: 'dependent',
        employee_id: employee.id,
        values: { relationship },
        ...relayed,
      });
      await refresh();
      landOn(answer.member.id, 'first_name');
    });

  const remove = (member) =>
    running('remove', async () => {
      await writes.settle();
      await removeMember(member.id);
      await refresh();
      toast.success(member.kind === 'employee' ? 'Employee (and dependents) removed' : 'Dependent removed');
    });

  const clear = () =>
    running('clear', async () => {
      await writes.settle();
      await clearRoster(dealId);
      onPage(1);
      await refresh();
      toast.success('The roster is cleared');
      return true;
    });

  async function undoMarks(activityId) {
    try {
      await revertActivity(activityId);
      toast.success('Undone');
    } catch (error) {
      toast.error(errorText(error));
    }
    refresh();
  }

  /** Marks on `refs` (the picked cells) or, with none, every open warning on the roster. Resolves true when done. */
  const mark = (action, refs = null, where = '') =>
    running('mark', async () => {
      await writes.settle();
      const reply = await postCensusMarks(dealId, { action, ...(refs ? { refs } : {}) });
      await refresh();
      const words = reviewToast(action, reply.changed, where);
      if (!reply.activity_id) toast.info(words);
      else {
        const undo = createElement(
          'button',
          { type: 'button', className: 'bnf-linklike', onClick: () => undoMarks(reply.activity_id) },
          'Undo',
        );
        toast.success(createElement('span', null, words, ' · ', undo), { duration: 10000 });
      }
      return true;
    });

  const missing = () => running('missing', async () => (await getMissing(dealId)).refs);

  const download = (name, path, done) =>
    running(name, async () => {
      await downloadFile(path, { fallbackName: 'census.xlsx' });
      toast.success(done);
    });

  return {
    busy,
    addEmployee,
    addDependent,
    remove,
    clear,
    mark,
    missing,
    template: () => download('template', censusTemplatePath(dealId), 'Census template downloaded'),
    exportCensus: () => download('export', censusExportPath(dealId), 'Census downloaded'),
  };
}
