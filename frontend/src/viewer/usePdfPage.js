import { useEffect, useRef, useState } from 'react';
import { extractPageText, findHighlightRanges } from './pdfFind';
import { geometryForOffsets, rectsForRange } from './pdfGeometry';

/*
 * Paint one page of a PDF on the canvas and box the value on it (plan.md §10.7; E22–E24). Ported from the old
 * PdfViewer's render effect, without OCR (browser OCR is slice 65; a scanned page says it could not locate the text).
 *
 * When the value is not on the page asked for: with a recorded page (the reader's or the locator's), the pages ±1 and
 * ±2 are tried ("Found on p. N (recorded as p. M)"); with none, every page is tried, and among the pages that print
 * it the one carrying most of the hint's words (the plan's carrier and name) wins ("Found on p. N").
 */

const MAX_SWEEP = 60; // pages searched when no page was recorded
const SCANNED_TEXT = 20; // a page with less text is a scan

let measureCtx = null;
/** How far into a run a character sits, by the run's font metrics (D-164); by count when nothing can measure. */
function measuredFraction(entry, at) {
  const raw = entry.item.str || '';
  const span = Math.max(1, entry.end - entry.start);
  const counted = Math.min(1, Math.max(0, at / span));
  if (raw.length !== span) return counted;
  if (!measureCtx) measureCtx = document.createElement('canvas').getContext('2d');
  if (!measureCtx) return counted;
  measureCtx.font = `100px ${entry.family || 'sans-serif'}`;
  const full = measureCtx.measureText(raw).width;
  if (!full) return counted;
  return Math.min(1, Math.max(0, measureCtx.measureText(raw.slice(0, Math.max(0, at))).width / full));
}

async function pageText(pdf, number, store) {
  if (!store.has(number)) {
    const page = await pdf.getPage(number);
    const { pageText: text, offsets } = extractPageText(await page.getTextContent());
    store.set(number, { text, offsets, geometry: geometryForOffsets(offsets) });
  }
  return store.get(number);
}

const hintScore = (text, hint) =>
  String(hint || '')
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((w) => w.length >= 3 && text.includes(w)).length;

/** The page that prints the value, or null: the neighbours of a recorded page, or every page by hint words. */
async function sweep(pdf, find, from, store, isCancelled) {
  const recorded = find.page;
  const pages = recorded
    ? [recorded + 1, recorded - 1, recorded + 2, recorded - 2]
    : Array.from({ length: Math.min(pdf.numPages, MAX_SWEEP) }, (_v, i) => i + 1);
  let best = null;
  for (const n of pages.filter((p, i, all) => p >= 1 && p <= pdf.numPages && p !== from && all.indexOf(p) === i)) {
    const page = await pageText(pdf, n, store);
    if (isCancelled()) return null;
    if (!findHighlightRanges(page.text, find.snippet, find.value, page.geometry, find.hint)) continue;
    if (recorded) return n;
    const score = hintScore(page.text, find.hint);
    if (!best || score > best.score) best = { n, score };
  }
  return best?.n ?? null;
}

/**
 * {highlights: {main, context}, state, foundOn, painted}. `state`: idle, searching, found (on the page asked for),
 * moved (the viewer moved itself; `onMove(n)` was called) or missing.
 */
export default function usePdfPage({ pdf, canvasRef, wrapRef, pageNum, scaleFor, find, findKey, onMove }) {
  const [result, setResult] = useState({ highlights: { main: [], context: [] }, state: 'idle', key: '' });
  const [paintedFor, setPaintedFor] = useState(null); // the document a page of which is on the canvas
  const textStore = useRef({ pdf: null, pages: new Map() });
  const swept = useRef('');
  const renderTask = useRef(null);

  useEffect(() => {
    if (!pdf || !canvasRef.current) return undefined;
    let cancelled = false;
    const target = Math.min(Math.max(1, pageNum), pdf.numPages);
    if (textStore.current.pdf !== pdf) textStore.current = { pdf, pages: new Map() };
    const store = textStore.current.pages;
    const settle = (state, highlights = { main: [], context: [] }) => {
      if (!cancelled) setResult({ highlights, state, key: findKey });
    };
    (async () => {
      const page = await pdf.getPage(target);
      if (cancelled) return;
      const viewport = page.getViewport({ scale: scaleFor(page.getViewport({ scale: 1 })) });
      const canvas = canvasRef.current;
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * dpr);
      canvas.height = Math.floor(viewport.height * dpr);
      canvas.style.width = `${Math.floor(viewport.width)}px`;
      canvas.style.height = `${Math.floor(viewport.height)}px`;
      renderTask.current?.cancel();
      const task = page.render({ canvas, canvasContext: canvas.getContext('2d'), viewport,
        transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined }); // prettier-ignore
      renderTask.current = task;
      try {
        await task.promise;
      } catch {
        return; // a newer render cancelled this one
      }
      if (cancelled) return;
      setPaintedFor(pdf);
      if (!find.value && !find.snippet) return settle('idle');
      const text = await pageText(pdf, target, store);
      if (cancelled) return;
      const match = findHighlightRanges(text.text, find.snippet, find.value, text.geometry, find.hint, {
        exact: find.exact,
      });
      if (match) {
        const boxes = (ranges) => ranges.flatMap((r) => rectsForRange(text.offsets, r, viewport, measuredFraction));
        const highlights = { main: boxes(match.ranges), context: boxes(match.contextRanges || []) };
        settle(target === (find.page || 1) ? 'found' : 'moved', highlights);
        if (highlights.main.length && wrapRef.current) {
          wrapRef.current.scrollTo({ top: Math.max(0, highlights.main[0].top - 120), behavior: 'smooth' });
        }
        return;
      }
      const from = find.page || 1;
      if (text.text.length >= SCANNED_TEXT && target === from && swept.current !== findKey) {
        swept.current = findKey;
        const n = await sweep(pdf, find, target, store, () => cancelled);
        if (cancelled) return;
        if (n) return onMove(n);
      }
      settle('missing');
    })();
    return () => {
      cancelled = true;
    };
    // `find` and `scaleFor` are read through findKey and the zoom/width they depend on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pdf, pageNum, findKey, scaleFor]);

  const current = result.key === findKey ? result : { highlights: { main: [], context: [] }, state: 'searching' };
  return { ...current, state: find.value || find.snippet ? current.state : 'idle', painted: paintedFor === pdf };
}
