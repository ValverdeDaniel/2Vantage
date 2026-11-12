import { useEffect, useState } from 'react';
import { pageCells, paperGeometry, printNotes } from './printedPage';
import WorkbookGrid from './WorkbookGrid';

function usePaperWidth(node) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!node) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(node);
    return () => observer.disconnect();
  }, [node]);
  return width;
}

/*
 * "Printed pages" in the Excel view (plan.md §8.14; J117; the old WorkbookPages.jsx at 891f1b3): a tab on letter
 * paper, page by page, as Excel prints it: the page chips, ‹ ›, the page number in the footer, the scale and the notes
 * about Fit To and a near edge. Where each page breaks is the server's (proposals/viewer/workbook_pages.py); this draws
 * one page at a time on its sheet of paper. The page picked starts again at 1 on another tab (`key` by the caller).
 */
export default function WorkbookPages({ tab, model }) {
  const info = tab.print;
  const pages = info?.pages || [];
  const [at, setAt] = useState(0);
  const [node, setNode] = useState(null);
  const stage = usePaperWidth(node);
  const page = pages[Math.min(at, pages.length - 1)];
  if (!info || !page) return <div className="bnf-xv-notice">This tab has no print setup to show.</div>;

  const { rows, cols, missing } = pageCells(info, page, tab.rows);
  const geometry = paperGeometry(info, tab.col_px, rows.length ? cols : [], stage);
  const notes = printNotes(info);
  return (
    <div className="bnf-xw-pages">
      <div className="bnf-xw-pages-head">
        <span>
          <b>
            Prints on {pages.length} page{pages.length === 1 ? '' : 's'} at {info.scale}%
          </b>{' '}
          · letter, {info.paper.w > info.paper.h ? 'landscape' : 'portrait'}
          {notes.length > 0 && <> · {notes.join('; ')}</>}
        </span>
        <span className="bnf-xv-spacer" />
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => setAt(Math.max(0, at - 1))}
          disabled={at <= 0}
          aria-label="Previous page"
        >
          ‹
        </button>
        <span>
          Page {page.n} of {pages.length}
        </span>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => setAt(Math.min(pages.length - 1, at + 1))}
          disabled={at >= pages.length - 1}
          aria-label="Next page"
        >
          ›
        </button>
      </div>
      {pages.length > 1 && pages.length <= 60 && (
        <div className="bnf-xw-pagechips" aria-label="Pages">
          {pages.map((p, i) => (
            <button
              key={p.n}
              type="button"
              className={`bnf-xv-chip ${i === at ? 'bnf-xv-chip-on' : ''}`}
              onClick={() => setAt(i)}
              title={`Rows ${p.rows[0] + 1}–${p.rows[1] + 1}`}
            >
              {p.n}
            </button>
          ))}
        </div>
      )}
      <div className="bnf-xw-paperstage" ref={setNode}>
        <div className="bnf-xw-paper" style={{ width: geometry.paperW, height: geometry.paperH }}>
          <div
            className="bnf-xw-print"
            style={{ left: geometry.left, top: geometry.top, transform: `scale(${geometry.k})` }}
          >
            <WorkbookGrid
              tab={tab}
              model={model}
              zoom={100}
              colScale={geometry.widen}
              headers={false}
              rows={rows}
              cols={cols}
            />
          </div>
          {info.footer === 'page' && (
            <div
              className="bnf-xw-footer"
              style={{ bottom: geometry.footerBottom, fontSize: geometry.footerSize }}
            >
              {page.n}
            </div>
          )}
          {missing && (
            <div className="bnf-xw-papernote">
              Rows past {tab.rows} are not drawn here; the download prints them all.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
