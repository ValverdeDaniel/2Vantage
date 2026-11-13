import { sentWords } from './receiptModel';
import { ThankYou } from './SubmitBar';

/*
 * After Submit (plan.md §8.20; L98, L99; the old roadmap's N1: "a receipt after Submit: what was sent as labels and
 * counts, when"; slice 59): the old thank-you card, then the receipt — what went through this link, by section, with
 * the time — on the to-do list's own rows (old `bnf-todo-*`, `bnf-progress-*`), and "Back to the form ▸", since the
 * link stays open to add or correct anything until it runs out. Without a receipt (an answer from before slice 59) the
 * thank-you stands alone.
 *
 * receipt: payload.receipt {at, sections [{key, title, lines}]} · short: the agency's first word · open: the link still
 * takes answers (not a lost or archived deal) · onBack()
 */
export default function Receipt({ receipt, short, open, onBack }) {
  return (
    <>
      <ThankYou short={short} />
      {receipt && receipt.sections.length > 0 && (
        <div className="bb-portal-card" role="region" aria-label="What you sent">
          <div className="bnf-progress-row" style={{ flexWrap: 'wrap', gap: 6 }}>
            <span className="bnf-progress-label">What you sent</span>
            <span className="bnf-progress-count">{sentWords(receipt.at)}</span>
          </div>
          <div className="bnf-todo-items">
            {receipt.sections.map((section) => (
              <div key={section.key} className="bnf-todo-item bnf-todo-item-done"
                   style={{ alignItems: 'flex-start', cursor: 'default' }}>
                <span className="bnf-todo-check">✓</span>
                <span className="bnf-todo-label" style={{ minWidth: 0, overflowWrap: 'anywhere' }}>
                  {section.title}
                  {section.lines.map((line) => (
                    <span key={line} className="bb-subtitle" style={{ display: 'block', fontWeight: 400 }}>
                      {line}
                    </span>
                  ))}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      {open && (
        <div className="bb-portal-footer" style={{ flexWrap: 'wrap', gap: 12 }}>
          <div className="bb-portal-lock">Need to add or correct something? The form is still open to you.</div>
          <div className="bnf-portal-actions">
            <button type="button" className="btn btn-secondary bb-portal-submit" onClick={onBack}>
              Back to the form ▸
            </button>
          </div>
        </div>
      )}
    </>
  );
}
