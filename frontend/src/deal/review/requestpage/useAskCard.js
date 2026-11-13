import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { reviewKey } from '../../../api/review';
import { planForm, useUpdateForm } from '../../../api/reviewForm';
import { useTrayAsk, useTrayRemove } from '../../../api/reviewTray';
import { errorText } from '../../../lib/errors';
import { useDebouncedValue } from '../../../lib/useDebouncedValue';
import { useToast } from '../../../ui/useToast';
import { bodyOf, changeCount, emptyChange, tickAction, updateWords, withOff } from './askCardModel';

/*
 * The Ask card's state on one open request (L36, L39, L42; old 891f1b3 `useLinkBuilder.js` link mode): a tick drafts
 * the item into the tray named for the request (or takes that draft out); an untick of what the link carries, the part
 * switches, the level, each person's settings and the note wait here, held per request, until Update link. The dry run
 * (350 ms after the last change, as the builder's) says the level it needs, what goes on and comes off, why it cannot
 * go, and the live numbers. Update link answers each new PIN once.
 */
export default function useAskCard(dealId, target) {
  const [changes, setChanges] = useState({});
  const [done, setDone] = useState(null);
  const ask = useTrayAsk(dealId);
  const remove = useTrayRemove(dealId);
  const update = useUpdateForm(dealId);
  const toast = useToast();
  const rid = target?.request_id;
  const change = changes[rid] || emptyChange();
  const body = target ? bodyOf(change, target) : null;
  const key = useDebouncedValue(JSON.stringify(body || {}), 350);
  const plan = useQuery({
    queryKey: reviewKey(dealId, 'request', 'plan', rid || '', key),
    queryFn: () => planForm(dealId, rid, JSON.parse(key)),
    enabled: Boolean(rid),
    staleTime: 0,
    placeholderData: (previous) => previous,
  });
  const set = (next) => setChanges((now) => ({ ...now, [rid]: typeof next === 'function' ? next(now[rid] || emptyChange()) : next }));
  const fail = (error) => toast.error(errorText(error));

  const tick = (item) => {
    const action = tickAction(item, target, change);
    if (action.kind === 'off' || action.kind === 'keep') set((now) => withOff(now, action.ref));
    else if (action.kind === 'undraft') remove.mutateAsync([action.id]).catch(fail);
    else ask.mutateAsync({ refs: [action.ref], request_id: rid }).catch(fail);
  };
  const addAll = (refs) => refs.length && ask.mutateAsync({ refs, request_id: rid, skip_out: true }).catch(fail);

  const run = () =>
    update
      .mutateAsync({ requestId: rid, ...bodyOf(change, target) })
      .then((answer) => {
        set(emptyChange());
        setDone(answer);
        toast.success('Their link is updated: their form shows it now, at the same address');
      })
      .catch(fail);

  const ready = key === JSON.stringify(body || {});
  const planned = ready ? plan.data : null;
  return {
    change,
    set,
    tick,
    addAll,
    plan: planned,
    planning: !ready || plan.isFetching,
    count: changeCount(change, target),
    busy: ask.isPending || remove.isPending || update.isPending,
    updating: update.isPending,
    updateLabel: updateWords(target, update.isPending),
    update: run,
    done,
    dismiss: () => setDone(null),
    reset: () => set(emptyChange()),
    waitingOn: planned?.refused || '',
  };
}
