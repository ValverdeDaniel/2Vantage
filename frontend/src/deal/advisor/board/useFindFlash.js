import { useEffect, useRef } from 'react';

const FLASH = 'bnf-find-flash';
const FLASH_MS = 1500;

/*
 * A found plan, brought into view and flashed (plan.md §8.14; F16; the old AdvisorTab's revealPlan): its row (its
 * column, transposed) scrolls into view when off screen and flashes for 1.5 s. Exactly one match on this line does
 * it on its own, once per plan (typing on, or the refetch after a star, never replays it); Enter on the finder does
 * it for the first plan drawn. Above 150 rows the board draws only what is in view, so the row is drawn first
 * (`win.reveal`). The class is toggled on the DOM, not held in state: the flash is a one-shot.
 */
function flash(container, planId, timers) {
  const cells = container ? Array.from(container.querySelectorAll(`[data-plan-id="${planId}"]`)) : [];
  if (!cells.length) return;
  const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  cells[0].scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'nearest', inline: cells[0].tagName === 'TH' ? 'center' : 'nearest' });
  for (const cell of cells) {
    window.clearTimeout(timers.get(cell));
    cell.classList.remove(FLASH);
  }
  cells[0].getBoundingClientRect(); // the reflow that lets the animation start over
  for (const cell of cells) {
    cell.classList.add(FLASH);
    timers.set(cell, window.setTimeout(() => cell.classList.remove(FLASH), FLASH_MS));
  }
}

export default function useFindFlash({ drawn, rowsLayout, win, scrollRef, soleHit }) {
  const timers = useRef(new WeakMap());
  const show = (planId) => {
    const run = () => flash(scrollRef.current, planId, timers.current);
    if (rowsLayout) win.reveal(drawn.findIndex((plan) => plan.id === planId), run);
    else run();
  };
  const latest = useRef(show);
  useEffect(() => {
    latest.current = show;
  });
  useEffect(() => {
    if (soleHit != null) latest.current(soleHit);
  }, [soleHit]);
  return show;
}
