import { useNavigate } from 'react-router';
import { waitingView } from './waitingView';

/**
 * "Whose court is the ball in" (M33; old `overview/WaitingBanner.jsx` at 891f1b3): Waiting on, With us or With them,
 * the words, how long, the next step when it says something else, and Go ▸ to the next step's tab and view. It sits
 * under the title, above the facts (X-84; OQ96's default), and reads the shell's journey (`journey`), never a second
 * read. Nothing on a lost deal (M34).
 */
export default function WaitingBanner({ journey }) {
  const navigate = useNavigate();
  const view = waitingView(journey);
  if (!view) return null;
  return (
    <div className={`bnf-next-banner bnf-ov-waiting bnf-next-${view.severity}`} role="status">
      <div className="bnf-ov-waiting-main">
        <div className="bnf-next-label">
          {view.done ? 'Status' : 'Waiting on'}
          {view.side && (
            <span className={`bnf-ov-side bnf-ov-side-${view.side}`}>{view.side === 'us' ? 'With us' : 'With them'}</span>
          )}
        </div>
        <div className="bnf-next-text">{view.label}</div>
        {view.detail && <div className="bnf-ov-waiting-detail">{view.detail}</div>}
        {view.next && <div className="bnf-ov-waiting-next">Next step — {view.next}</div>}
      </div>
      {view.link && !view.done && (
        <button type="button" className="btn btn-primary btn-sm" onClick={() => navigate(view.link)}>
          Go ▸
        </button>
      )}
    </div>
  );
}
