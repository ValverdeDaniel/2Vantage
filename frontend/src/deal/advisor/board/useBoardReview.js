import { createElement, useState } from 'react';
import { useNavigate } from 'react-router';
import { cellCounts, flaggedKeys } from '../../../valuereview/marksCache';
import { reviewToast, targetWords } from '../../../valuereview/reviewWords';
import useMarks from '../../../valuereview/useMarks';
import { useRecheck } from '../../claude';
import { useToast } from '../../../ui/useToast';
import UndoNote from './UndoNote';

/*
 * Reviewing on the board (plan.md §8.14; F63, F65, F67; the old AdvisorTab's flag menu and bulk review): the flags
 * chip's own Approve, Ignore and Needs checking for one quote, and the review strip over the quotes being looked at —
 * the ticked plans, else the plans the finder and filters show, else every plan on the line (F65; the strip names
 * which). Each review is one Activity row; its toast offers Undo (F67, E54). The counts are the server's flags on the
 * compact cells (`s`, `m`), so the board agrees with the station (OQ28). Nothing on the board waits on a review. The
 * strip's ✦ Ask Claude to re-check (F66; slice 22) re-reads those quotes' flagged values; a person applies its card.
 */
export default function useBoardReview({ dealId, comparison, meta, lineLabel, drawn, ticked, filtering }) {
  const toast = useToast();
  const navigate = useNavigate();
  const marks = useMarks(dealId, { toastDone: false });
  const claude = useRecheck(dealId);
  const [menu, setMenu] = useState(null);
  const fields = Object.fromEntries((meta.plans?.fields ?? []).map((field) => [field.key, field]));
  const keys = (comparison.groups ?? []).flatMap((group) => group.fields);

  let targets;
  let target;
  if (ticked.length) {
    targets = ticked;
    target = targetWords({ ticked: ticked.length });
  } else if (filtering) {
    targets = drawn;
    target = targetWords({ filtered: drawn.length });
  } else {
    targets = comparison.plans;
    target = targetWords({ line: lineLabel });
  }

  async function review(action, planIds, where) {
    const answer = await marks.run(action, { plan_ids: planIds }, { where });
    setMenu(null);
    if (!answer?.changed) return;
    const done = { action, changed: answer.changed, activityId: answer.activity_id };
    const onUndo = () => marks.undo(done);
    toast.success(createElement(UndoNote, { text: reviewToast(action, answer.changed, where), onUndo }), {
      duration: 10000,
    });
  }

  return {
    busy: marks.busy,
    menu,
    toggle: (planId) => setMenu((now) => (now === planId ? null : planId)),
    field: (key) => fields[key],
    flagged: (plan) => flaggedKeys(plan, keys),
    plan: (action, plan) => review(action, [plan.id], `${plan.carrier} ${plan.name}`.trim()),
    view: (plan, key) => {
      const doc = comparison.documents?.[plan.cells?.[key]?.d];
      if (!doc) return;
      const query = new URLSearchParams({ doc: String(doc.id), ref: `plan:${plan.id}:${key}` });
      navigate(`/deals/${dealId}/documents?${query}`);
    },
    strip: {
      counts: cellCounts(targets.flatMap((plan) => Object.values(plan.cells ?? {}))),
      target,
      onAction: (action) => review(action, targets.map((plan) => plan.id), target),
      recheck: claude && { ...claude, run: () => claude.run({ planIds: targets.map((plan) => plan.id) }) },
    },
  };
}
