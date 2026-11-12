import { useState } from 'react';
import { useChatMessages, useChats, useSendMessage } from '../../api/chats';
import { current as boardNow } from '../shared/boardBridge';
import { current as viewerNow } from '../shared/viewerBridge';

/*
 * The drawer's chat state (plan.md §8.17, §10.6; D7, D19; the old ScanChat): which chat is open — the one this person
 * last wrote in on the deal (the server's pick, the old D-096 rule), another picked in Chats ▾, or ＋ New chat, a draft
 * the server numbers on its first message — its messages, and sending. A message carries the tab and, on the Advisor,
 * what the board shows (F108) or what the Export viewer shows (J120), so Claude answers about what the person sees.
 * One turn runs per deal at a time (the chat lane): `running` is it, and the composer waits for it (D19).
 */
export default function useChat({ dealId, tab, model, state }) {
  const chats = useChats(dealId);
  const [picked, setPicked] = useState(null); // null: the server's pick; 'new': a draft; else a chat id
  const list = chats.data?.chats || [];
  const chatId = picked ?? chats.data?.open ?? list[0]?.id ?? 'new';
  const messages = useChatMessages(chatId === 'new' ? null : chatId);
  const sending = useSendMessage(dealId);
  const running = (state?.jobs || []).find((job) => job.kind === 'turn') || null;

  async function send(text, options = {}) {
    const sent = await sending.mutateAsync({
      text,
      chatId: chatId === 'new' ? null : chatId,
      tab,
      board: tab === 'advisor' ? boardNow(dealId) : null,
      viewer: tab === 'advisor' ? viewerNow(dealId) : null,
      model,
      ...options,
    });
    setPicked(sent.chat_id);
    return sent;
  }

  return {
    list,
    chatId,
    current: list.find((chat) => chat.id === chatId) || null,
    loading: chats.isLoading,
    window: chats.data?.window ?? 30,
    messages,
    running,
    busy: Boolean(running) || sending.isPending,
    send,
    pick: setPicked,
  };
}
