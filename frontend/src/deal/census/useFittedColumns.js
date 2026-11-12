import { useEffect, useMemo, useState } from 'react';

/*
 * Grid column headers never truncate (plan.md §8.21; C2: "headers size the columns"; the old utils/columnHeaders.js
 * at 891f1b3): a label sets in one or two lines, and a column too narrow for two is widened to fit. A column's own
 * width (`width` from /api/meta/, the old registry's) stays a floor; nothing here makes a column narrower. The type
 * and chrome below are `.bb-col-header`'s: change them together, or the measured width stops matching the drawn one.
 */
const HEADER_TYPE = '600 11.5px';
const HEADER_CHROME = 21; // 10px padding each side + the 1px right border
const SAFETY = 3; // sub-pixel rounding between canvas and layout

let canvasContext;

function headerFont() {
  const family = getComputedStyle(document.body).fontFamily || 'sans-serif';
  return `${HEADER_TYPE} ${family}`;
}

function measure(text) {
  if (canvasContext === undefined) canvasContext = document.createElement('canvas').getContext('2d');
  if (!canvasContext) return text.length * 6.6;
  canvasContext.font = headerFont();
  return canvasContext.measureText(text).width;
}

// The narrowest width that sets `label` in at most two lines, breaking only between words.
function headerTextWidth(label) {
  const words = String(label || '').trim().split(/\s+/).filter(Boolean);
  if (!words.length) return 0;
  let best = measure(words.join(' '));
  for (let i = 1; i < words.length; i += 1) {
    best = Math.min(best, Math.max(measure(words.slice(0, i).join(' ')), measure(words.slice(i).join(' '))));
  }
  return best;
}

const noExtra = () => 0;

function headerFontReady() {
  return !document.fonts?.check || document.fonts.check(headerFont());
}

/** The columns, each `width` raised to what its header needs; `extra(col)` is the room beside the label (a hint). */
export default function useFittedColumns(columns, extra = noExtra) {
  const [fontReady, setFontReady] = useState(headerFontReady);
  useEffect(() => {
    if (fontReady || !document.fonts?.load) return undefined;
    let live = true;
    document.fonts.load(headerFont()).then(
      () => live && setFontReady(true),
      () => {},
    );
    return () => {
      live = false;
    };
  }, [fontReady]);
  return useMemo(
    () =>
      (columns || []).map((col) => {
        const need = Math.ceil(headerTextWidth(col.label) + HEADER_CHROME + extra(col) + SAFETY);
        return need > (col.width || 0) ? { ...col, width: need } : col;
      }),
    // fontReady re-measures once the web font has loaded: it is a trigger, not an input.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [columns, extra, fontReady],
  );
}
