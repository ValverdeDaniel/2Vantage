import { useState } from 'react';

/*
 * The PDF viewer's toolbar (plan.md §8.16; E22, E24, E25): ‹ Prev, the page box, Next ›, − ＋ Fit, and what the find
 * said, in the old app's words and classes (a scanned page: "Locating on the scanned image…", then "Located").
 */
export default function PdfToolbar({ pageNum, numPages, onPage, zoom, onZoom, state, moved }) {
  const [draft, setDraft] = useState(null);
  return (
    <div className="bb-pdf-toolbar">
      <button type="button" className="bb-pdf-btn" disabled={pageNum <= 1} onClick={() => onPage(pageNum - 1)}>
        ‹ Prev
      </button>
      <span className="bb-pdf-pageinfo">
        Page{' '}
        <input
          className="bb-pdf-pageinput bb-mono"
          aria-label="Page number"
          value={draft ?? String(pageNum)}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== 'Enter') return;
            const n = parseInt(draft ?? '', 10);
            setDraft(null);
            if (!Number.isNaN(n)) onPage(n);
          }}
          onBlur={() => setDraft(null)}
        />{' '}
        of {numPages || '…'}
      </span>
      <button
        type="button"
        className="bb-pdf-btn"
        disabled={!numPages || pageNum >= numPages}
        onClick={() => onPage(pageNum + 1)}
      >
        Next ›
      </button>
      <button
        type="button"
        className="bb-pdf-btn"
        title="Zoom out"
        onClick={() => onZoom((z) => Math.max(0.4, (z ?? 1) * 0.8))}
      >
        −
      </button>
      <button
        type="button"
        className="bb-pdf-btn"
        title="Zoom in"
        onClick={() => onZoom((z) => Math.min(4, (z ?? 1) * 1.25))}
      >
        ＋
      </button>
      <button
        type="button"
        className="bb-pdf-btn"
        title="Fit the page to the panel width"
        disabled={zoom === null}
        onClick={() => onZoom(null)}
      >
        Fit
      </button>
      {state === 'missing' && (
        <span className="bb-pdf-notfound-inline">⚠ Couldn&apos;t locate the exact text on this page.</span>
      )}
      {state === 'reading' && (
        <span className="bb-pdf-ocrnote">⏳ Locating on the scanned image… (the first time can take ~15s)</span>
      )}
      {state === 'ocr' && <span className="bb-pdf-foundnote">✓ Located on the scanned image</span>}
      {state === 'moved' && moved && (
        <span className="bb-pdf-foundnote">
          ✓ Found on p. {moved.found}
          {moved.recorded ? ` (recorded as p. ${moved.recorded})` : ''}
        </span>
      )}
    </div>
  );
}
