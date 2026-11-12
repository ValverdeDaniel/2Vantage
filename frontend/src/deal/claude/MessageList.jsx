import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { send as sendBoard } from '../shared/boardBridge';
import { runLine, windowHint } from './chatWords';
import { secondsSince, SLOW_NOTE } from './drawerWords';
import OverBudget from './OverBudget';
import TurnChanges from './TurnChanges';

/*
 * A chat's messages (plan.md §8.17, §10.6; D21, D24, D25, D80, D90; the old ScanChat's scroll): each person's message
 * says who wrote it (chats are the deal's); Claude's reply carries what it proposed (TurnChanges), "▸ Show on the
 * board" when it set the board, and its run line for everyone ("This run $x · Deal $y of $25 · Sonnet 5.5"). A turn
 * the deal's budget stopped shows the over-budget card under the message (Run anyway for admins and direct people).
 * While Claude answers, "Thinking… Ns", with "a big request can take a minute" after 30 s. Past 30 messages, the hint
 * that Claude reads only the last 30. A chat that fails to load offers Retry.
 */
function Thinking({ since }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const handle = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(handle);
  }, []);
  const seconds = since ? secondsSince(since, now) : 0;
  return (
    <div className="bnf-advisor-msg bnf-advisor-msg-assistant bb-empty" role="status">
      <span className="bb-dot-pulse" aria-hidden="true" /> Thinking… {seconds}s
      {seconds >= 30 && <span className="bnf-thinking-note"> — {SLOW_NOTE}</span>}
    </div>
  );
}

function Message({ dealId, chatId, message, meta, state, onBoard }) {
  const turn = message.turn;
  const mine = message.role === 'user';
  return (
    <div className={`bnf-advisor-msg bnf-advisor-msg-${message.role}`} data-message={message.id}>
      {mine && message.author && <div className="bnf-msg-author">{message.author.name}</div>}
      {message.text}
      {mine && turn?.land === 'budget' && turn.status === 'done' && (
        <OverBudget
          dealId={dealId}
          job={{ id: turn.id, model: turn.model, wait_reason: turn.wait_reason }}
          canOverride={Boolean(state?.can?.opus)}
          onDismiss={() => {}}
        />
      )}
      {mine && turn?.status === 'failed' && <div className="bnf-msg-cost">Claude stopped: {turn.error}</div>}
      {!mine && turn && <TurnChanges dealId={dealId} chatId={chatId} turn={turn} />}
      {!mine && turn?.board && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => onBoard(turn.board)}>
          ▸ Show on the board
        </button>
      )}
      {!mine && turn && <div className="bnf-msg-cost">{runLine(turn, state?.spend, meta)}</div>}
    </div>
  );
}

export default function MessageList({ dealId, chat, meta, state }) {
  const navigate = useNavigate();
  const scroll = useRef(null);
  const rows = chat.messages.data?.messages || [];
  const asking = chat.running && rows.some((row) => row.job_id === chat.running.id);
  useEffect(() => {
    if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [rows.length, asking]);

  const onBoard = (board) => {
    if (!sendBoard(dealId, board)) navigate(`/deals/${dealId}/advisor`);
  };

  return (
    <>
      <div className="bnf-scanchat-scroll" ref={scroll}>
        {chat.messages.isError && (
          <div className="bnf-scanchat-loaderr">
            <span>This chat could not be loaded.</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => chat.messages.refetch()}>
              Retry
            </button>
          </div>
        )}
        {!rows.length && !chat.messages.isError && (
          <div className="bb-subtitle">
            Ask about the deal, or tell Claude what to change: “Show PPOs under $40,000 a month”, “delete the duplicate
            Aetna plan”, “the client wants to keep Aetna”.
          </div>
        )}
        {rows.map((message) => (
          <Message
            key={message.id}
            dealId={dealId}
            chatId={chat.chatId}
            message={message}
            meta={meta}
            state={state}
            onBoard={onBoard}
          />
        ))}
        {asking && <Thinking since={chat.running.started_at} />}
      </div>
      {windowHint(chat.current?.messages || rows.length, chat.window) && (
        <div className="bnf-chat-window-hint">{windowHint(chat.current?.messages || rows.length, chat.window)}</div>
      )}
    </>
  );
}
