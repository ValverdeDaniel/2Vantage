import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useDecide, useReviewBoard } from '../../../api/review';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import { approvedWords } from '../queue/queueWords';
import { returnedOf, returnText, sectionNumbers, taking } from './sectionModel';

const LANES = [
  { key: 'review', tone: 'violet', label: 'to review' },
  { key: 'waiting', tone: 'amber', label: 'waiting on the client' },
  { key: 'missing', tone: 'rose', label: 'missing' },
];

/*
 * The section bar at the top of Intake and Census (plan.md §8.8; L14, C34; old 891f1b3 `ReviewSectionBar.jsx` and
 * `SectionReviewBar.jsx`): the section's lane counts with "Review & requests · all sections ▸", and — once something
 * came back — the violet line ("↩ Dana answered 3 · 2 ready · 1 still typing") with Review ▸ and "Approve N ready ✓",
 * which takes the submitted answers, and an idle link's too with its tick (D-153 C4). Its numbers are the Board's
 * (`sections`). To review opens the section's queue on the Review & requests tab; waiting and missing open its Board
 * (the section's own Board and Missing lane are slice 57's). The Next line joins with slice 56. Hidden while the counts
 * load; a deal that may no longer ask its client approves nothing (L129).
 */
export default function SectionBar({ dealId, surface, label }) {
  const board = useReviewBoard(dealId);
  const decide = useDecide(dealId);
  const navigate = useNavigate();
  const toast = useToast();
  const [withIdle, setWithIdle] = useState(false);
  if (!board.data) return null;
  const section = board.data.sections?.[surface];
  const counts = sectionNumbers(section);
  const returned = returnedOf(section);
  const cameBack = returned.answered + returned.questions > 0;
  const canApprove = returned.ready > 0 && !board.data.asks_closed;
  const takes = taking(returned, withIdle && returned.readyIdle > 0);
  const review = `/deals/${dealId}/review`;
  const onLane = (lane) => navigate(lane === 'review' ? `${review}?view=queue&section=${surface}` : review);

  const approve = async () => {
    try {
      const body = { door: 'approve', surface, ready_only: true, include_idle: withIdle && returned.readyIdle > 0 };
      const answer = await decide.mutateAsync(body);
      toast.success(approvedWords(answer.approved.length));
      setWithIdle(false);
    } catch (error) {
      toast.error(errorText(error));
    }
  };

  return (
    <div className="rr-sbar" aria-label={`${label}: review and requests`}>
      <div className="rr-sbar-line rr-sbar-counts">
        {LANES.map((lane) => (
          <button
            key={lane.key}
            type="button"
            className={`rr-sbar-count rr-sbar-count-${lane.tone}`}
            onClick={() => onLane(lane.key)}
          >
            <span className="rr-sbar-dot" aria-hidden="true">
              ●
            </span>{' '}
            {counts[lane.key]} {lane.label}
          </button>
        ))}
        {counts.inTray > 0 && <span className="rr-sbar-tray">· {counts.inTray} in the tray</span>}
        <button type="button" className="rr-sbar-board" onClick={() => navigate(review)}>
          Review &amp; requests · all sections ▸
        </button>
      </div>
      {cameBack && (
        <div className="rr-sbar-line rr-sbar-return">
          <span className="rr-sbar-return-text">{returnText(returned)}</span>
          <span className="rr-sbar-actions">
            <button type="button" className="btn btn-violet btn-sm" onClick={() => onLane('review')}>
              Review ▸
            </button>
            {canApprove && returned.readyIdle > 0 && (
              <label className="rr-idle-tick" title="Answers on a link nobody submitted, saved over a day ago">
                <input
                  type="checkbox"
                  checked={withIdle}
                  disabled={decide.isPending}
                  onChange={(event) => setWithIdle(event.target.checked)}
                />
                and {returned.readyIdle} not submitted · idle
              </label>
            )}
            {canApprove && (
              <button
                type="button"
                className="btn btn-secondary btn-sm rr-sbar-approve"
                disabled={decide.isPending || !takes}
                onClick={approve}
              >
                {decide.isPending ? 'Approving…' : `Approve ${takes} ready ✓`}
              </button>
            )}
          </span>
        </div>
      )}
    </div>
  );
}
