// When a chat turn ends (plan.md §10.6; D35, D80, F108; slice 24): its chat refetches (Claude's reply, what it
// proposed and how that landed), the plans it changed flash once the deal's queries settle, and a board it set goes to
// the Advisor's board — at once when the board is on screen, else the Advisor opens and applies it as it mounts.
import api from '../../api/client';
import { jobKey } from '../../api/ai';
import { chatsKey } from '../../api/chats';
import { send as sendBoard } from '../shared/boardBridge';
import { flashWhenSettled } from './flashPlans';

export async function afterTurn(queryClient, dealId, job, openBoard) {
  queryClient.invalidateQueries({ queryKey: ['ai-chat'] });
  queryClient.invalidateQueries({ queryKey: chatsKey(dealId) });
  if (job.landed?.plan_ids?.length) flashWhenSettled(queryClient, dealId, job.landed.plan_ids);
  if (job.status !== 'done') return;
  const full = await queryClient.fetchQuery({
    queryKey: jobKey(job.id),
    queryFn: async () => (await api.get(`ai/jobs/${job.id}/`)).data,
    staleTime: 0,
  });
  const board = full?.result?.board;
  if (board && !sendBoard(dealId, board)) openBoard();
}
