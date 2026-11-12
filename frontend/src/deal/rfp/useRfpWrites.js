import { useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { markRfpCard, patchRfp, rfpKey } from '../../api/rfp';
import { errorStatus, errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { adopt, optimistic } from './requestModel';

/*
 * The RFP page's writes (plan.md §7.11; K9, K10, K25–K27; K.6 frontend). A request edit shows at once (optimistic) and
 * the server's answer is written into the cache; while another edit is still out, the answer waits, and the last one
 * to land refetches instead, so an answer that left the server earlier never paints over a later click (K.5 #2). A
 * refused value says "That value was not accepted" (K27) and the page refetches what is stored. The controls never
 * disable while a save is out (K26, bug 3). Marks answer every mark; the old page's queue is gone (K11).
 */
export default function useRfpWrites(dealId, fundingOrder) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const key = rfpKey(dealId);
  const writing = [...key, 'write'];
  const behind = useRef(false);

  const patch = useMutation({
    mutationKey: writing,
    mutationFn: (body) => patchRfp(dealId, body),
    onSuccess: (answer) => {
      if (queryClient.isMutating({ mutationKey: writing }) > 1) {
        behind.current = true;
        return;
      }
      if (behind.current) {
        behind.current = false;
        queryClient.invalidateQueries({ queryKey: key, exact: true });
        return;
      }
      queryClient.setQueryData(key, (page) => (page ? adopt(page, answer) : page));
    },
    onError: (error) => {
      const refused = errorStatus(error) === 400;
      const fallback = 'Could not save the request.';
      toast.error(refused ? 'That value was not accepted' : errorText(error, { fallback }));
      queryClient.invalidateQueries({ queryKey: key, exact: true });
    },
  });

  const mark = useMutation({
    mutationFn: (body) => markRfpCard(dealId, body),
    onSuccess: (answer) => queryClient.setQueryData(key, (page) => (page ? { ...page, done: answer.done } : page)),
    onError: (error) => toast.error(errorText(error, { fallback: 'Could not save the completed mark.' })),
  });

  return {
    // The click shows in the same frame (a blur's text never flickers back); a refetch in flight cannot paint over it.
    save: (body) => {
      queryClient.cancelQueries({ queryKey: key, exact: true });
      queryClient.setQueryData(key, (page) => (page ? optimistic(page, body, fundingOrder) : page));
      patch.mutate(body);
    },
    mark: (card, done, options) => mark.mutate({ card, done }, options),
    marking: mark.isPending,
  };
}
