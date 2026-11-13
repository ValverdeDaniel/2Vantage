// Where the comment margin's cards go (plan.md §8.8; L31; old 891f1b3 `CommentMargin.jsx` `placeCards`). Pure:
// `wants` (each item's top, in page order), the cards' `heights`, the picked card's index (-1 for none) and the gap.
// The picked card lines up with its item exactly and the others make room above and below it; with none picked, each
// sits at its item or under the card above. With no room above the picked card, everything goes from the top.

export function placeCards(wants, heights, active, gap) {
  const n = wants.length;
  const tops = new Array(n);
  const forward = (from, floor) => {
    let next = floor;
    for (let i = from; i < n; i += 1) {
      tops[i] = Math.max(wants[i], next);
      next = tops[i] + heights[i] + gap;
    }
  };
  if (active < 0) {
    forward(0, 0);
    return tops;
  }
  tops[active] = Math.max(0, wants[active]);
  forward(active + 1, tops[active] + heights[active] + gap);
  let ceiling = tops[active] - gap;
  for (let i = active - 1; i >= 0; i -= 1) {
    tops[i] = Math.min(wants[i], ceiling - heights[i]);
    ceiling = tops[i] - gap;
  }
  if (n && tops[0] < 0) forward(0, 0);
  return tops;
}

/**
 * The cards the margin holds, in the form's order: the items with a conversation or an answer to look at, and the one
 * picked (a card is never blank per question). `items` the tab's, `threads` {ref: [note]}.
 */
export function marginRefs(items, threads, picked) {
  return (items || [])
    .filter((item) => item.ref === picked || (threads?.[item.ref] || []).length > 0 || item.status === 'answered' || item.status === 'question')
    .map((item) => item.ref);
}
