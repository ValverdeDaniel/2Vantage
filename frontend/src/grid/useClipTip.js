import { useState } from 'react';

/*
 * The full value of a cut cell, on hover (plan.md §8.21; F36's three-line clip; the old useGridSizes' useClipTip).
 * A sized grid wraps each value in `.bnf-clip`; `show` (onMouseEnter) reads whether the box cuts its text and, if
 * so, holds the whole text for a fixed `.bb-tooltip` at the cell's top centre. Read on hover, never during render.
 */

/** The whole text of a cell whose `.bnf-clip` box cuts it, or '' when it all shows. */
export function clippedText(cell) {
  const box = cell?.querySelector?.('.bnf-clip');
  if (!box) return '';
  const cut = box.scrollHeight > box.clientHeight + 1 || box.scrollWidth > box.clientWidth + 1;
  return cut ? (box.textContent || '').replace(/\s+/g, ' ').trim() : '';
}

export default function useClipTip() {
  const [tip, setTip] = useState(null); // {x, y, text}
  const show = (event) => {
    const text = clippedText(event.currentTarget);
    if (!text) return;
    const rect = event.currentTarget.getBoundingClientRect();
    setTip({ x: rect.left + rect.width / 2, y: rect.top, text });
  };
  const hide = () => setTip(null);
  return { tip, show, hide };
}
