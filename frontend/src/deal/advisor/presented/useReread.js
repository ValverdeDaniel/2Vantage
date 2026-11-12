import { useAiState, useStartRead } from '../../../api/ai';
import { useDocuments } from '../../../api/documents';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import { quoteFileIds } from './presentedModel';

/*
 * ⟲ Re-read quotes on the Proposal tab (plan.md §8.15; J80, Simplify: an ai job; the old ComparisonGrid's
 * handleReExtract): offered only with Claude set up (D26) and quote files on the deal. One read of every quote file
 * through the one read door, which always waits for review here (E75): nothing on the table changes until a person
 * uses it. The deal's AI poll (useAiState) follows it; the Claude strip shows its progress and Stop.
 */
export default function useReread(dealId, meta) {
  const toast = useToast();
  const ai = useAiState(dealId);
  const documents = useDocuments(dealId);
  const start = useStartRead(dealId);
  const ids = quoteFileIds(documents.data, meta);

  async function run() {
    try {
      await start.mutateAsync({ documentIds: ids, target: 'quotes', review: true });
      toast.info('Claude is reading the quotes again; the read waits for your review before anything changes.');
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not start the quote reader' }));
    }
  }

  return { available: Boolean(ai.data?.claude && meta?.ai && ids.length), busy: start.isPending, run };
}
