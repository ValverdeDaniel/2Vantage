import { useCallback, useEffect, useRef, useState } from 'react';
import Highlights from './Highlights';
import PdfToolbar from './PdfToolbar';
import usePdfDocument, { megabytes } from './usePdfDocument';
import usePdfPage from './usePdfPage';

/*
 * A PDF, with the value boxed (plan.md §8.16; E22–E24): canvas, Prev / page box / Next, zoom 0.4–4× and Fit, refit on
 * resize. `find` is {page, value, snippet, hint, exact}: the page to open (the locator's or the reader's), the value
 * to box, the reader's line (drawn fainter), the plan's carrier and name (which column), and whether the server found
 * the figure once on that page. `jumpKey` re-runs the same find (a second ↗ on the same value flashes it again).
 * Takes a URL (same origin) or bytes. The root says what it is doing: data-render loading|ready|error, data-find
 * idle|searching|found|moved|missing.
 */
export default function PdfViewer({ url, data, find = {}, jumpKey = 0, onPageChange }) {
  const { pdf, error, progress } = usePdfDocument({ url, data });
  const startPage = Math.max(1, find.page || 1);
  const findKey = [url, find.page, find.value, find.snippet, find.hint, find.exact, jumpKey].join('|');
  // The page on screen belongs to one find: a new value, page or file opens its own page again.
  const [paging, setPaging] = useState({ key: findKey, page: startPage, moved: null });
  const { page: pageNum, moved } = paging.key === findKey ? paging : { page: startPage, moved: null };
  const [zoom, setZoom] = useState(null); // null: fit the panel's width (the viewer is keyed by file)
  const [wrapW, setWrapW] = useState(0);
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);

  // Re-render when the panel's width changes (resize, Expand); rounded so sub-pixel reflow cannot loop.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver((entries) => {
      const width = Math.round(entries[0]?.contentRect?.width || 0);
      if (width) setWrapW(width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [pdf]);

  const scaleFor = useCallback(
    (base) => {
      const width = wrapW ? wrapW - 26 : base.width;
      const fit = Math.min(2, Math.max(0.5, width / base.width));
      return Math.min(4, Math.max(0.4, (zoom ?? 1) * fit));
    },
    [zoom, wrapW],
  );

  const onMove = useCallback(
    (n) => {
      setPaging({ key: findKey, page: n, moved: { found: n, recorded: find.page || null } });
      onPageChange?.(n);
    },
    [findKey, find.page, onPageChange],
  );

  const shown = usePdfPage({ pdf, canvasRef, wrapRef, pageNum, scaleFor, find, findKey, onMove });

  function goTo(n) {
    const page = Math.min(Math.max(1, n), pdf?.numPages || 1);
    setPaging({ key: findKey, page, moved: null });
    onPageChange?.(page);
  }

  if (!url && !data) return null;
  if (error) {
    return (
      <div className="bb-pdf-notfound" data-render="error" role="alert">
        {error}
      </div>
    );
  }
  return (
    <div
      className="bb-pdf-viewer"
      data-render={shown.painted ? 'ready' : 'loading'}
      data-viewer-page={pageNum}
      data-find={shown.state}
    >
      <PdfToolbar
        pageNum={pageNum}
        numPages={pdf?.numPages || 0}
        onPage={goTo}
        zoom={zoom}
        onZoom={setZoom}
        state={shown.state}
        moved={moved}
      />
      <div className="bb-pdf-canvas-wrap" ref={wrapRef}>
        <div className="bb-pdf-page">
          {!pdf && (
            <div className="bb-pdf-loading" role="status">
              {progress?.loaded > 0
                ? `Loading document · ${megabytes(progress.loaded)}${
                    progress.total ? ` of ${megabytes(progress.total)}` : ''
                  } MB…`
                : 'Loading document…'}
            </div>
          )}
          <canvas ref={canvasRef} />
          <Highlights boxes={shown.highlights} flashKey={`${jumpKey}-${pageNum}`} />
        </div>
      </div>
    </div>
  );
}
