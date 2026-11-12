// Work with Claude's chats and the deal's AI settings (plan.md §7.5; D7, D19, D25, D100, D104; slice 24).
// Keys: ['deal', id, 'ai', 'chats'] for the deal's chats · ['ai-chat', chatId] for one chat's messages.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { aiKey, jobKey, watchJob } from './ai';
import { dealKey, invalidateDeal } from './deals';

export const chatsKey = (dealId) => dealKey(dealId, 'ai', 'chats');
export const messagesKey = (chatId) => ['ai-chat', Number(chatId)];

/** The deal's chats, most recently used first: {chats, open (the chat this person last wrote in), window}. */
export function useChats(dealId) {
  return useQuery({
    queryKey: chatsKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/ai/chats/`)).data,
    staleTime: 0,
  });
}

/** One chat's latest messages, oldest first, each with its turn: {chat, messages, more}. */
export function useChatMessages(chatId) {
  return useQuery({
    queryKey: messagesKey(chatId),
    queryFn: async () => (await api.get(`ai/chats/${chatId}/messages/`)).data,
    enabled: Boolean(chatId),
    staleTime: 0,
  });
}

/**
 * Send a message (D19): ({text, chatId, documentIds, tab, board, model, budgetOverride}) → {chat_id, message, job,
 * queue_position}. The turn runs in the chat lane; useAiState watches it until it ends.
 */
export function useSendMessage(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ text, chatId, documentIds, tab, board, model, budgetOverride }) =>
      (
        await api.post(`deals/${dealId}/ai/messages/`, {
          text,
          ...(chatId ? { chat_id: chatId } : {}),
          ...(documentIds?.length ? { document_ids: documentIds } : {}),
          ...(tab ? { tab } : {}),
          ...(board ? { board } : {}),
          ...(model ? { model } : {}),
          ...(budgetOverride ? { budget_override: true } : {}),
        })
      ).data,
    onSuccess: (sent) => {
      watchJob(dealId, sent.job);
      queryClient.invalidateQueries({ queryKey: chatsKey(dealId) });
      queryClient.invalidateQueries({ queryKey: messagesKey(sent.chat_id) });
      queryClient.invalidateQueries({ queryKey: aiKey(dealId) });
    },
  });
}

/** ✎ Rename (D7): ({chatId, title}) → {id, title, named}; '' gives back "Chat N". */
export function useRenameChat(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ chatId, title }) => (await api.patch(`ai/chats/${chatId}/`, { title })).data,
    onSuccess: (chat) => {
      queryClient.invalidateQueries({ queryKey: chatsKey(dealId) });
      queryClient.invalidateQueries({ queryKey: messagesKey(chat.id) });
    },
  });
}

/** The table lock (D104) and the deal's budget (D100, admins only): ({locked} | {budget_usd}) → the state. */
export function useDealAiSettings(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.patch(`deals/${dealId}/ai/`, body)).data,
    onSuccess: (state) => {
      queryClient.setQueryData(aiKey(dealId), state);
      queryClient.invalidateQueries({ queryKey: dealKey(dealId, 'activity') });
    },
  });
}

/** A turn's changes applied or undone (D72, D73 for a turn): ({jobId, select} | {jobId}) → refetch the deal and chat. */
function useTurnLanding(dealId, chatId, path) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ jobId, select }) =>
      (await api.post(`ai/jobs/${jobId}/${path}/`, select ? { select } : {})).data,
    onSuccess: ({ job }) => {
      queryClient.setQueryData(jobKey(job.id), job);
      if (chatId) queryClient.invalidateQueries({ queryKey: messagesKey(chatId) });
      invalidateDeal(queryClient, dealId, { header: true });
    },
  });
}

export const useApplyTurn = (dealId, chatId) => useTurnLanding(dealId, chatId, 'apply');
export const useUndoTurn = (dealId, chatId) => useTurnLanding(dealId, chatId, 'undo');

/** Discard a turn's waiting changes: (jobId) → the job. */
export function useDiscardTurn(dealId, chatId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (jobId) => (await api.post(`ai/jobs/${jobId}/discard/`)).data,
    onSuccess: () => {
      if (chatId) queryClient.invalidateQueries({ queryKey: messagesKey(chatId) });
      queryClient.invalidateQueries({ queryKey: aiKey(dealId) });
    },
  });
}
