// Flash the plans Claude just changed (plan.md §8.17; D35, F112; the old shared/flashPlans.js, D-118): every
// `[data-plan-id]` cell or row of those plans inside `container` (the deal's `bnf-claude-section`), without scrolling:
// the person may be reading another part of the table, and Claude's change never moves them. The class is toggled on
// the DOM, not held in state, so a re-render after a refetch never replays it; a flash already running restarts.
// Reduced motion is the stylesheet's job (.bnf-claude-flash).

export const CLAUDE_FLASH_CLASS = 'bnf-claude-flash';
const FLASH_MS = 2400;
const timers = new WeakMap();

export default function flashPlans(container, planIds) {
  if (!container || !planIds?.length) return 0;
  const found = [];
  [...new Set(planIds.map(String))].forEach((id) => {
    container.querySelectorAll(`[data-plan-id="${CSS.escape(id)}"]`).forEach((el) => found.push(el));
  });
  if (!found.length) return 0;
  found.forEach((el) => {
    window.clearTimeout(timers.get(el));
    el.classList.remove(CLAUDE_FLASH_CLASS);
  });
  found[0].getBoundingClientRect(); // the reflow that lets the animation start over
  found.forEach((el) => {
    el.classList.add(CLAUDE_FLASH_CLASS);
    timers.set(
      el,
      window.setTimeout(() => el.classList.remove(CLAUDE_FLASH_CLASS), FLASH_MS),
    );
  });
  return found.length;
}

/**
 * After a landing: once the deal's queries have settled (two quiet looks, as the old landClaude waited for its table),
 * flash the plans on the deal page's section. Automatic landings flash too: their plan ids ride the finished job.
 */
export function flashWhenSettled(queryClient, dealId, planIds) {
  if (!planIds?.length) return;
  let quiet = 0;
  let looks = 0;
  const look = () => {
    quiet = queryClient.isFetching({ queryKey: ['deal', Number(dealId)] }) ? 0 : quiet + 1;
    looks += 1;
    if (quiet >= 2 || looks > 200) {
      window.requestAnimationFrame(() => flashPlans(document.querySelector('.bnf-claude-section'), planIds));
    } else {
      window.setTimeout(look, 60);
    }
  };
  window.setTimeout(look, 60);
}
