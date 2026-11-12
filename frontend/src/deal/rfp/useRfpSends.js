import { useMutation, useQueryClient } from '@tanstack/react-query';
import { dealKey } from '../../api/deals';
import { markDraftSent, rfpKey } from '../../api/rfp';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { optimisticSent } from './drafts/draftsModel';

/*
 * The Sent tick (plan.md §5.7 "Sent"; K64–K68, K120): it shows at once, the server's answer (the drafts and the marks)
 * is written into the page, and the deal's header refetches, since the first send moves the deal to Quoting. A refusal
 * (a lost deal, a past year) says why and the page refetches what is stored.
 */
export default function useRfpSends(dealId) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const key = rfpKey(dealId);
  const mutation = useMutation({
    mutationFn: ({ draft, sent }) => markDraftSent(dealId, draft, sent),
    onMutate: ({ draft, sent }) => {
      queryClient.cancelQueries({ queryKey: key, exact: true });
      const shown = (page) => (page ? { ...page, drafts: optimisticSent(page.drafts, draft, sent) } : page);
      queryClient.setQueryData(key, shown);
    },
    onSuccess: (answer) => {
      queryClient.setQueryData(key, (page) => (page ? { ...page, drafts: answer.drafts, done: answer.done } : page));
      queryClient.invalidateQueries({ queryKey: dealKey(dealId, 'header') });
    },
    onError: (error) => {
      toast.error(errorText(error, { fallback: 'Could not record the send.' }));
      queryClient.invalidateQueries({ queryKey: key, exact: true });
    },
  });
  const busy = mutation.isPending ? mutation.variables?.draft : '';
  return { mark: (draft, sent) => mutation.mutate({ draft, sent }), busy };
}
