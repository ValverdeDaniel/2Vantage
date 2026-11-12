import { useState } from 'react';
import { useRenameChat } from '../../api/chats';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { chatOption, lastUsedLine } from './chatWords';

/*
 * Chats ▾ (plan.md §8.17; D7; the old chatControls ChatBar): the deal's chats, most recently used first, each "title ·
 * tab · day" with who last wrote in it on hover; ＋ New chat (a draft until its first message); ✎ Rename, so everyone
 * on the deal can find it ("Aetna fixes"). Every chat sees the deal's documents, plans and guidance.
 */
export default function ChatBar({ dealId, chat, disabled }) {
  const toast = useToast();
  const rename = useRenameChat(dealId);
  const [naming, setNaming] = useState(null);
  const draft = chat.chatId === 'new';
  const listed = draft ? [{ id: 'new', title: 'New chat' }, ...chat.list] : chat.list;

  async function save() {
    try {
      await rename.mutateAsync({ chatId: chat.chatId, title: naming });
      setNaming(null);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <div className="bnf-chatbar">
      <div className="bnf-chatbar-row">
        {naming === null ? (
          <select
            className="bnf-chatbar-chats"
            value={chat.chatId}
            disabled={disabled}
            aria-label="Chats"
            onChange={(event) => chat.pick(event.target.value === 'new' ? 'new' : Number(event.target.value))}
            title={[
              "Chats on this deal, most recently used first. Each keeps its own history; the deal's documents, plans and guidance are in every one.",
              lastUsedLine(chat.current),
            ]
              .filter(Boolean)
              .join(' ')}
          >
            {listed.length === 0 && <option value="new">New chat</option>}
            {listed.map((row) => (
              <option key={row.id} value={row.id}>
                {row.id === 'new' ? row.title : chatOption(row)}
              </option>
            ))}
          </select>
        ) : (
          <input
            className="bnf-chatbar-chats"
            value={naming}
            maxLength={80}
            autoFocus
            aria-label="Chat name"
            placeholder="Name this chat"
            onChange={(event) => setNaming(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') save();
              if (event.key === 'Escape') {
                event.stopPropagation();
                setNaming(null);
              }
            }}
          />
        )}
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={disabled || draft}
          onClick={() => chat.pick('new')}
          title="Start a fresh conversation. Claude still sees the deal's documents, plans and guidance."
        >
          ＋ New chat
        </button>
        {chat.current && naming === null && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={disabled}
            onClick={() => setNaming(chat.current.named ? chat.current.title : '')}
            title="Name this chat, so everyone on the deal can find it"
          >
            ✎ Rename
          </button>
        )}
        {naming !== null && (
          <button type="button" className="btn btn-primary btn-sm" disabled={rename.isPending} onClick={save}>
            Save
          </button>
        )}
      </div>
    </div>
  );
}
