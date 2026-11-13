import { useTrayAsk } from '../../../api/reviewTray';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import Lane from './Lane';

const NAMES_SHOWN = 6;

/*
 * The Missing lane (rose; plan.md §8.8; L6; old 891f1b3 `DealReviewTab.jsx`): what the deal still needs from the client
 * and nobody has — the required census values by column, the intake's questions required to market, the checklist's
 * files not on file, each questionnaire's blank required answers with "＋ Ask them to fill it out online" (slice 58,
 * G76; the server's `ask_label`) (and, on the census's own board, "No census on file yet") — each with how many have a question
 * open, Open ▸ and "＋ Ask all", which puts what is not asked yet in the request tray (the server's `ask`; nothing goes
 * out until it is sent) and hides once nothing is left. The counts are the server's.
 */
export default function MissingLane({ dealId, rows, onGo, readOnly }) {
  const ask = useTrayAsk(dealId);
  const toast = useToast();
  const total = (rows || []).reduce((sum, row) => sum + row.count, 0);
  const askAll = (row) => {
    const body = row.ask.census ? { census: row.ask.census } : { refs: row.ask.refs, skip_out: true };
    ask
      .mutateAsync(body)
      .then((answer) => toast.success(`${answer.added} added to the request tray`))
      .catch((error) => toast.error(errorText(error)));
  };
  return (
    <Lane title="Missing" tone="rose" count={total} empty="Nothing required is missing.">
      {(rows || []).map((row) => (
        <div key={row.key} className={`bnf-board-card${row.questions_open ? ' bnf-board-card-q' : ''}`}>
          <div className="bnf-board-card-head">
            <span className="bnf-board-section">{row.section}</span>
            {row.questions_open > 0 && (
              <span className="bnf-q-chip" title={`${row.questions_open} question(s) from the client waiting on our answer`}>
                ? {row.questions_open}
              </span>
            )}
            <span className="rr-pill-count">{row.count}</span>
          </div>
          <div className="bnf-board-card-text">{row.label}</div>
          {row.items.length > 0 && (
            <div className="bnf-review-note">
              {row.items.slice(0, NAMES_SHOWN).join(' · ')}
              {row.items.length > NAMES_SHOWN ? ` · +${row.items.length - NAMES_SHOWN} more` : ''}
            </div>
          )}
          <div className="bnf-board-card-actions">
            <button type="button" className="bnf-override-link" title="See what is missing" onClick={() => onGo(row.fix)}>
              Open ▸
            </button>
            {!readOnly && row.ask && (
              <button
                type="button"
                className="bnf-ask-btn"
                disabled={ask.isPending}
                title={`Put the ${row.left} not asked yet in the request tray: nothing goes out until you send it from the request page`}
                onClick={() => askAll(row)}
              >
                {row.ask_label || (row.left === 1 ? '＋ Ask' : `＋ Ask all ${row.left}`)}
              </button>
            )}
          </div>
        </div>
      ))}
    </Lane>
  );
}
