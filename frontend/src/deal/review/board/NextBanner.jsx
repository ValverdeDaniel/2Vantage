import { useState } from 'react';
import { labelIn } from '../reviewModel';

/*
 * Next → (plan.md §8.8; L3, L4, L25; old 891f1b3 `DealReviewTab.jsx` `bnf-board-next`, `RequestNext.jsx`): the one
 * thing to do first, from the server's ranking (`rules/next.py`), with Go ▸ and Skip — Skip lasts this visit, held
 * here. A link running out also offers Extend at once (L25). Nothing ranked says so. `where` names the board's scope
 * ("the census") in that line; `kinds` is /api/meta/ `review.next_kinds`.
 */
export default function NextBanner({ entries, kinds, where = 'this deal', onGo, onExtend, readOnly }) {
  const [skip, setSkip] = useState(0);
  const list = entries || [];
  const next = list[skip];
  if (!next) {
    return <div className="bnf-board-next bnf-board-next-clear">✓ Nothing on {where} needs you first.</div>;
  }
  return (
    <div className={`bnf-board-next bnf-board-next-${next.kind}`} role="status">
      <span className="bnf-board-next-label">Next →</span>
      <span className="bnf-board-next-kind">{labelIn(kinds, next.kind)}</span>
      <span className="bnf-board-next-text">
        <b>{next.label}</b> · {next.why}
      </span>
      <span className="bnf-board-next-actions">
        {next.kind === 'link_expiring' && !readOnly && onExtend && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            title="Give the link its life again from today, never past its 30-day limit"
            onClick={() => onExtend({ link_id: next.link_id, name: '' })}
          >
            Extend
          </button>
        )}
        <button type="button" className="btn btn-primary btn-sm" title="Do this first" onClick={() => onGo(next.fix)}>
          Go ▸
        </button>
        {list.length > skip + 1 && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            title="Show the next thing to do instead, for this visit only: nothing is saved"
            onClick={() => setSkip(skip + 1)}
          >
            Skip
          </button>
        )}
      </span>
    </div>
  );
}
