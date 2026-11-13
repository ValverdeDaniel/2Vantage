import { useEffect, useState } from 'react';
import { askQuestions, detailOf, postSeen } from './portalApi';
import { askableItems, hasNews, needWords, newWords, whoWords } from './threadModel';

const SEEN_AFTER_MS = 5000; // what is new counts as seen once it was on screen this long (L103)

function day(at) {
  const date = at ? new Date(at) : null;
  return date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
}

function Ask({ items, fixed = null, readOnly, onAsk, onCancel }) {
  const [ref, setRef] = useState(fixed || items[0]?.ref || '');
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  async function send() {
    if (!text.trim() || !ref || sending) return;
    setSending(true);
    setError((await onAsk(ref, text.trim())) || '');
    setSending(false);
  }
  return (
    <div className="bnf-fu-ask">
      {!fixed && (
        <select value={ref} aria-label="What your question is about" disabled={readOnly} onChange={(event) => setRef(event.target.value)}>
          {items.map((item) => (
            <option key={item.ref} value={item.ref}>
              {item.label}
            </option>
          ))}
        </select>
      )}
      <textarea autoFocus placeholder="Ask your broker about this item…" maxLength={1000} value={text} disabled={readOnly} onChange={(event) => setText(event.target.value)} />
      {error && <div className="bnf-issue-line bb-rose">{error}</div>}
      <div>
        <button type="button" className="btn btn-primary btn-sm" disabled={readOnly || sending || !text.trim()} onClick={send}>
          {sending ? 'Sending…' : 'Send'}
        </button>{' '}
        <button type="button" className="btn btn-secondary btn-sm" disabled={sending} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

/*
 * Follow-ups and questions on the client's page (plan.md §8.20; L81, L101, L103, L106; old 891f1b3
 * `BenefitsClientPortal.jsx` `FollowUps`, `ItemThread`): a card per item we wrote to them about or they asked about,
 * with its thread ("You asked", "A colleague asked", or the agency — never one of our names), whether it needs their
 * answer, and "Ask a question" on it; and "Ask a question about…" any item the page shows. Their words render as text.
 * Something of ours new to them counts as seen once it was on screen a few seconds (`seen/`). A preview only reads.
 */
export default function FollowUps({ token, page, short, readOnly }) {
  // The cards a question's answer brought, until the page is read again (a poll, a save) and brings its own.
  const [asked, setAsked] = useState(null); // {from: the page's cards, cards}
  const [asking, setAsking] = useState(null); // a card's ref, or 'any'
  const items = askableItems(page);
  const cards = asked && asked.from === page.follow_ups ? asked.cards : page.follow_ups || [];
  const news = hasNews(cards);
  useEffect(() => {
    if (readOnly || !news) return undefined;
    const timer = setTimeout(() => postSeen(token).catch(() => {}), SEEN_AFTER_MS);
    return () => clearTimeout(timer);
  }, [news, readOnly, token]);

  async function ask(ref, text) {
    try {
      const answer = await askQuestions(token, [{ ref, text }]);
      setAsked({ from: page.follow_ups, cards: answer.follow_ups });
      setAsking(null);
      return '';
    } catch (error) {
      const data = error?.response?.data;
      return detailOf(error) || (Array.isArray(data?.questions) ? data.questions[0] : '') || 'That did not go through. Please try again.';
    }
  }

  if (!cards.length && !items.length) return null;
  const need = needWords(cards);
  return (
    <div id="bnf-sec-followups" className="bb-portal-card bnf-fu-list bnf-fu-summary">
      <div>
        <div className="bb-panel-title">Follow-ups from {short}</div>
        <div className="bb-panel-sub">
          {cards.length ? `Answers we asked you to check again, and your questions${need ? ` — ${need}` : ''}.` : 'Not sure about something on this page? Ask your broker here.'}
        </div>
      </div>
      {cards.map((card) => (
        <div key={card.ref} className={`bnf-fu-row${newWords(card) ? ' bnf-fu-row-new' : ''}`}>
          <div className="bnf-fu-h">
            <b>{card.title}</b>
            {newWords(card) && (
              <span className="bnf-qcard-newtag">
                <i aria-hidden="true" />
                {newWords(card)}
              </span>
            )}
            {card.needs_answer && <span className="bnf-fu-badge bnf-fu-badge-need">Needs your answer</span>}
            {!card.needs_answer && card.answered && <span className="bnf-fu-badge bnf-fu-badge-done">Answered</span>}
            {card.question_open && <span className="bnf-fu-badge">Question open — with {short}</span>}
          </div>
          {card.thread.map((entry, index) => (
            <div key={`${entry.at}-${index}`} className={entry.who === 'agency' ? 'bnf-fu-note' : 'bnf-fu-asked'}>
              <span>
                {whoWords(entry, short)}
                {day(entry.at) ? ` · ${day(entry.at)}` : ''}
              </span>
              {entry.text}
            </div>
          ))}
          {asking === card.ref ? (
            <Ask items={items} fixed={card.ref} readOnly={readOnly} onAsk={ask} onCancel={() => setAsking(null)} />
          ) : (
            <div className="bnf-qcard-actions">
              <button type="button" className="bnf-qcard-ask" disabled={readOnly} onClick={() => setAsking(card.ref)}>
                Ask a question
              </button>
            </div>
          )}
        </div>
      ))}
      {items.length > 0 &&
        (asking === 'any' ? (
          <Ask items={items} readOnly={readOnly} onAsk={ask} onCancel={() => setAsking(null)} />
        ) : (
          <div className="bnf-qcard-actions">
            <button type="button" className="bnf-qcard-ask" disabled={readOnly} onClick={() => setAsking('any')}>
              Ask a question about…
            </button>
          </div>
        ))}
    </div>
  );
}
