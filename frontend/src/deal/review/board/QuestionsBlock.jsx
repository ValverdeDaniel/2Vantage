import { agoWords } from '../reviewModel';

/*
 * The client's open questions on the Board (plan.md §8.8; L5; old 891f1b3 `DealReviewTab.jsx` `bnf-board-questions`):
 * the oldest six, each with its section, what it is about, who asked, when, a 140-character excerpt and Answer ▸, which
 * opens the request page on its tab, where the reply goes back on their link; "+N more ▸" opens it on the first.
 */
export default function QuestionsBlock({ board, onRequest }) {
  const questions = board.questions || [];
  const total = board.questions_total || 0;
  if (!questions.length) return null;
  return (
    <div className="bnf-board-questions">
      <div className="bnf-board-questions-head">
        <span className="bnf-q-mark" aria-hidden="true">
          ?
        </span>
        <b>
          {total} question{total === 1 ? '' : 's'} from the client
        </b>
        <span className="bnf-review-note">waiting on our answer</span>
      </div>
      {questions.map((question) => (
        <div key={question.note_id} className="bnf-board-question">
          <div className="bnf-board-question-body">
            <div className="bnf-board-question-where">
              <span className="bnf-board-section">{question.section}</span>
              <b>{question.where}</b>
            </div>
            {question.excerpt && <div className="bnf-board-question-text">“{question.excerpt}”</div>}
            <div className="bnf-review-note">
              {question.who ? `${question.who} · ` : ''}asked {agoWords(question.at)}
            </div>
          </div>
          <button
            type="button"
            className="btn btn-violet btn-sm"
            title="Answer it: opens the request page, where your reply goes back on their link"
            onClick={() => onRequest(question.fix.pane)}
          >
            Answer ▸
          </button>
        </div>
      ))}
      {total > questions.length && (
        <button type="button" className="bnf-override-link" onClick={() => onRequest(questions[0].fix.pane)}>
          +{total - questions.length} more ▸
        </button>
      )}
    </div>
  );
}
