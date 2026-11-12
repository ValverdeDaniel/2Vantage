import { useQueryClient } from '@tanstack/react-query';
import { createElement } from 'react';
import { dealKey, useRevertActivity } from '../../../api/deals';
import { boardExport, useCopyPlan, useCreateRenewal, useSetSold } from '../../../api/quotes';
import {
  useClearLine,
  useClearShortlist,
  useDeletePlans,
  useMoveLine,
  useOrderPlans,
  useSetLinks,
  useSetRole,
  useStar,
} from '../../../api/quotesBoard';
import { downloadFile } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import * as bookingBridge from '../../shared/bookingBridge';
import UndoNote from './UndoNote';

/*
 * What the board's buttons do (plan.md §8.14; F43, F50–F55, F57–F61, F81, F93): each calls its door, words the
 * answer in the old toasts, and offers Undo through the `activity_id` the write returns. Refusals arrive as the
 * server's sentence (409). `lineLabel(key)` names a line; `line` is the board's.
 */

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

export default function useBoardActions(dealId, line, lineLabel) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const doors = {
    star: useStar(dealId),
    shortlist: useClearShortlist(dealId),
    role: useSetRole(dealId),
    links: useSetLinks(dealId),
    order: useOrderPlans(dealId),
    remove: useDeletePlans(dealId),
    clear: useClearLine(dealId),
    moveLine: useMoveLine(dealId),
    renewal: useCreateRenewal(dealId),
    copy: useCopyPlan(dealId),
    sold: useSetSold(dealId),
    revert: useRevertActivity(dealId),
  };
  const here = lineLabel(line);

  const failed = (error) => {
    toast.error(errorText(error));
    return null;
  };
  const undoable = (text, activityId) => {
    const onUndo = activityId
      ? () =>
          doors.revert
            .mutateAsync(activityId)
            .then(() => toast.success('Undone'))
            .catch(failed)
      : null;
    toast.success(createElement(UndoNote, { text, onUndo }), { duration: 10000 });
  };
  const changed = (answer, fallback) => answer?.plans?.length ?? fallback;

  return {
    busy: {
      star: doors.star.isPending,
      role: doors.role.isPending,
      remove: doors.remove.isPending || doors.clear.isPending,
      moveLine: doors.moveLine.isPending,
      order: doors.order.isPending,
      links: doors.links.isPending,
    },
    toggleStar: (plan) =>
      doors.star.mutateAsync({ planIds: [plan.id], starred: !plan.starred }).catch(failed),
    star: (planIds, starred) =>
      doors.star
        .mutateAsync({ planIds, starred })
        .then((answer) => {
          const n = changed(answer, planIds.length);
          undoable(`${plural(n, 'plan')} ${starred ? 'starred' : 'unstarred'} on ${here}`, answer?.activity_id);
          return answer;
        })
        .catch(failed),
    setRole: (planIds, role) =>
      doors.role
        .mutateAsync({ planIds, role })
        .then((answer) => {
          const n = changed(answer, planIds.length);
          const what = role === 'current' ? 'marked current' : 'no longer current';
          undoable(`${plural(n, 'plan')} ${what} on ${here}`, answer?.activity_id);
          return answer;
        })
        .catch(failed),
    moveLine: (planIds, target) =>
      doors.moveLine
        .mutateAsync({ planIds, line: target })
        .then((answer) => {
          undoable(`${plural(planIds.length, 'plan')} moved to ${lineLabel(target)}`, answer?.activity_id);
          return answer;
        })
        .catch(failed),
    remove: (planIds) =>
      doors.remove
        .mutateAsync(planIds)
        .then((answer) => {
          const n = answer?.removed?.length ?? 0;
          undoable(`${plural(n, 'plan')} removed from ${here}${answer?.note ? ` — ${answer.note}` : ''}`, answer?.activity_id);
          return answer;
        })
        .catch(failed),
    clearLine: () =>
      doors.clear
        .mutateAsync(line)
        .then((answer) => {
          const n = answer?.removed?.length ?? 0;
          undoable(`${plural(n, 'plan')} removed from ${here}${answer?.note ? ` — ${answer.note}` : ''}`, answer?.activity_id);
          return answer;
        })
        .catch(failed),
    clearShortlist: () =>
      doors.shortlist
        .mutateAsync(line)
        .then((answer) => undoable(`Shortlist cleared on ${here}`, answer?.activity_id))
        .catch(failed),
    move: (plan, step, among) =>
      doors.order.mutateAsync({ line, move: { plan_id: plan.id, step, among } }).catch(failed),
    link: (plan, replacesIds) => doors.links.mutateAsync({ planId: plan.id, replacesIds }).catch(failed),
    createRenewal: (plan) =>
      doors.renewal
        .mutateAsync(plan.id)
        .then(() => toast.success('Renewal created'))
        .catch(failed),
    copy: (plan) =>
      doors.copy
        .mutateAsync(plan.id)
        .then(() => toast.success('Duplicated, with its rates'))
        .catch(failed),
    setSold: (plan, sold) => {
      // The booking summary opens when this sale first makes the deal Sold (H35), never on every Sold toggle (bug 27).
      const first = sold && queryClient.getQueryData(dealKey(dealId, 'header'))?.stage !== 'sold';
      return doors.sold
        .mutateAsync({ planId: plan.id, sold })
        .then((answer) => {
          toast.success(sold ? `${plan.name} marked sold` : `${plan.name} un-sold`);
          if (first && answer?.deal?.stage === 'sold') bookingBridge.open(dealId);
        })
        .catch(failed);
    },
    viewBooking: () => bookingBridge.open(dealId), // the sold plan's "Booked · view" (H35)
    exportBoard: (params) => {
      const { url, params: query } = boardExport(dealId, params);
      return downloadFile(url, { params: query, fallbackName: 'quote-comparison.xlsx' })
        .then(() => toast.success('Quote comparison downloaded'))
        .catch(failed);
    },
  };
}
