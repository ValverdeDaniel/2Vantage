import { useRef, useState } from 'react';
import { useReviewQueue } from '../../../api/review';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import ReviewQueue from '../../../valuereview/ReviewQueue';
import useItemThread from '../thread/useItemThread';
import { QUEUE_KEYS } from '../../../valuereview/queueModel';
import useReviewHotkeys from '../../../valuereview/useReviewHotkeys';
import GroupChips from './GroupChips';
import ItemDetail from './ItemDetail';
import QueueBars, { QueuePager } from './QueueBars';
import { cfgFor, renderSummary } from './queueItems';
import { DECIDED, focusOf, keepDecided } from './queueWords';
import useQueueDecisions from './useQueueDecisions';

const TITLES = { to_review: 'From the client', in_progress: 'Not submitted yet', going_back: 'Going back' };
const EMPTY = {
  to_review: 'Nothing from the client is waiting for review.',
  in_progress: 'Nobody is part-way through a link.',
  going_back: 'Nothing is waiting on the client to answer again.',
};

/*
 * One section's client answers (plan.md §8.8; L11, L15, L16, L20, B38, C28, C32; old 891f1b3 `CensusClientReview.jsx`
 * and `IntakeQueue.jsx`): the phase tabs (To review · Not submitted yet), the groups by column or section and change
 * with the picked group's "Approve all N ✓", the keyboard queue, and its pages. Not submitted yet only reads. Each row
 * keeps its mark for the visit; an approval offers ↶ Undo (C28). Slice 56: X sends an answer back with a note (into
 * the request tray), N writes a team note, each item shows its thread, and Going back lists what went back until the
 * client answers again (still decidable: an approval closes what was sent back).
 */
export default function SectionQueue({ dealId, meta, surface, readOnly = false }) {
  const [phase, setPhase] = useState('to_review');
  const [group, setGroup] = useState('');
  const [page, setPage] = useState(1);
  const [focusId, setFocusId] = useState(null);
  const queue = useReviewQueue(dealId, { surface, phase, group, page });
  const decisions = useQueueDecisions(dealId);
  const thread = useItemThread(dealId, { readOnly });
  const queueRef = useRef(null);
  const fresh = (queue.data?.items || []).map((item, index) => ({ ...item, id: item.ref, index }));
  const items = keepDecided(fresh, decisions.decided, { phase, group });
  const focus = focusOf(items, focusId, decisions.decided);
  const reviewing = phase !== 'in_progress' && !readOnly;
  useReviewHotkeys({
    enabled: items.length > 0,
    onKey: (action) => queueRef.current?.act(action),
    keys: QUEUE_KEYS,
  });

  if (queue.isPending) return <Loading label="Loading what the client sent…" />;
  if (queue.isError) return <InlineError title="The review queue" error={queue.error} onRetry={() => queue.refetch()} />;
  const data = queue.data;
  const changes = Object.fromEntries((meta?.changes || []).map((entry) => [entry.key, entry.label]));
  const kindWords = Object.fromEntries((meta?.note_kinds || []).map((entry) => [entry.key, entry.label]));
  const groups = data.groups.map((entry) => ({ ...entry, sub: changes[entry.change] || entry.change }));
  const picked = groups.find((entry) => entry.key === group);
  const decided = Object.fromEntries(
    Object.entries(decisions.decided).map(([id, mark]) => [id, withUndo(mark, id, items, decisions)]),
  );
  const pick = (next) => {
    setGroup(next || '');
    setPage(1);
  };

  return (
    <div className="bnf-client-review">
      <QueueBars
        meta={meta}
        data={data}
        phase={phase}
        onPhase={(next) => {
          setPhase(next);
          setGroup('');
          setPage(1);
        }}
      />
      <ReviewQueue
        ref={queueRef}
        title={TITLES[phase]}
        items={items}
        focusId={focus}
        onFocus={setFocusId}
        renderSummary={(item) => renderSummary(item, changes)}
        renderDetail={(item) => (
          <ItemDetail
            item={item}
            kindWords={kindWords}
            threadProps={(ref, ask) => thread.propsFor({ ref, ask })}
          />
        )}
        cfgFor={cfgFor}
        onDecide={decisions.onDecide}
        decided={decided}
        busyId={decisions.busyId}
        readOnly={!reviewing}
        header={
          <GroupChips
            label={surface === 'census' ? 'By column' : 'By section'}
            groups={groups}
            active={group || null}
            allCount={groups.reduce((sum, entry) => sum + entry.count, 0)}
            onPick={pick}
            approve={
              reviewing && picked
                ? {
                    label: decisions.busy ? 'Approving…' : `Approve all ${picked.count} ✓`,
                    disabled: decisions.busy || !data.ids.length,
                    onClick: async () => (await decisions.approveAll(data.ids)) && pick(''),
                  }
                : null
            }
          />
        }
        keyLabels={{ a: 'approve', x: 'send back', r: 'later' }}
        emptyNote={EMPTY[phase]}
        doneNote="Approved answers are stored with the client as their source."
      />
      <QueuePager pages={data.page} onPage={setPage} />
    </div>
  );
}

function withUndo(mark, id, items, decisions) {
  if (mark.status !== 'approved') return mark;
  const item = items.find((entry) => entry.id === id);
  if (!item || item.kind === 'block') return mark;
  const after = (
    <>
      {' · '}
      <button
        type="button"
        className="bnf-linklike"
        disabled={decisions.busyId != null}
        title="Take the approval back: the value it replaced comes back, and the answer waits again"
        onClick={(event) => {
          event.stopPropagation();
          decisions.undo(item);
        }}
      >
        ↶ Undo
      </button>
    </>
  );
  return { ...mark, ...DECIDED.approved, after };
}
