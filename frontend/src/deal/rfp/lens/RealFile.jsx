import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { fetchRfpLook } from '../../../api/rfp';
import { errorText } from '../../../lib/errors';
import cx from '../../../ui/cx';
import { useModalLayer } from '../../../ui/useModalLayer';
import SheetTable from '../../../viewer/SheetTable';

const SUB =
  "Built exactly as the download and the packet build it. Formula cells read blank here — the carrier's own sheet " +
  'computes them when it opens.';

/* Sheet tabs, "Rows a–b of n" and the window's ◂ Prev / Next ▸, as the document viewer draws them. */
function Toolbar({ data, go, loading }) {
  const lastStart = Math.max(0, data.total_rows - data.window);
  return (
    <div className="bb-pdf-toolbar bnf-sheet-toolbar">
      <span className="bnf-sheet-tabs" role="tablist" aria-label="Sheets">
        {data.sheets.map((sheet) => (
          <button
            key={sheet.name}
            type="button"
            role="tab"
            aria-selected={sheet.name === data.sheet}
            className={cx('bb-pdf-btn', sheet.name === data.sheet && 'bnf-sheet-tab-on')}
            onClick={() => sheet.name !== data.sheet && go({ sheet: sheet.name, start: 0 })}
          >
            {sheet.name}
            {sheet.hidden && <span className="bnf-sheet-hidtag">hidden</span>}
          </button>
        ))}
      </span>
      {loading && <span className="bnf-spin" aria-hidden="true" />}
      <span className="bb-pdf-pageinfo">
        Rows {data.total_rows ? data.start + 1 : 0}–{Math.min(data.start + data.window, data.total_rows)} of{' '}
        {data.total_rows}
      </span>
      <button
        type="button"
        className="bb-pdf-btn"
        disabled={data.start <= 0}
        onClick={() => go({ sheet: data.sheet, start: Math.max(0, data.start - data.window) })}
      >
        ◂ Prev
      </button>
      <button
        type="button"
        className="bb-pdf-btn"
        disabled={data.start >= lastStart}
        onClick={() => go({ sheet: data.sheet, start: Math.min(lastStart, data.start + data.window) })}
      >
        Next ▸
      </button>
    </div>
  );
}

/*
 * "Check the real file" (plan.md §8.12; K82; old CensusFormatLens.jsx CheckModal at 891f1b3, `bb-modal
 * bnf-lens-check`): the carrier's file built exactly as the download builds it, shown as the document viewer shows a
 * sheet — Excel's look, sheet tabs, 200-row windows — with every warning, including what only the fill knows (a
 * formula cell we refuse to overwrite). It opens on the roster sheet; a format with a CSV switches between the two.
 * Escape or the backdrop closes it. The server logs the view.
 */
export default function RealFile({ dealId, format, onClose }) {
  const ref = useRef(null);
  const titleId = useId();
  useModalLayer(ref, { onEscape: onClose, focusField: false });
  const kinds = format.file_formats;
  const [kind, setKind] = useState(kinds[0]);
  const [where, setWhere] = useState({});
  const [shown, setShown] = useState({ data: null, error: '', loading: true });
  const key = kind === kinds[0] ? format.key : `${format.key}-${kind}`;

  useEffect(() => {
    let live = true;
    fetchRfpLook(dealId, key, where)
      .then((data) => live && setShown({ data, error: '', loading: false }))
      .catch((error) => live && setShown({ data: null, error: errorText(error), loading: false }));
    return () => {
      live = false;
    };
  }, [dealId, key, where]);

  const { data, error, loading } = shown;
  // The last window stays on screen while the next one is built, so focus (and Escape) stay in the dialog.
  const go = (next) => {
    setShown((now) => ({ ...now, loading: true }));
    setWhere(next);
  };
  return createPortal(
    <div className="progress-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId} className="bb-modal bnf-lens-check">
        <div className="bb-modal-header">
          <div>
            <div id={titleId} className="bb-modal-title">
              {format.label} — the real file
            </div>
            <div className="bb-modal-sub">{SUB}</div>
          </div>
          <div className="rpt-compare-actions">
            {kinds.length > 1 &&
              kinds.map((each) => (
                <button
                  key={each}
                  type="button"
                  className={cx('bnf-wq-chip', kind === each && 'bnf-wq-chip-on')}
                  onClick={() => {
                    if (each === kind) return;
                    setKind(each);
                    go({});
                  }}
                >
                  {each.toUpperCase()}
                </button>
              ))}
            <button type="button" className="bb-pdf-btn" title="Close" aria-label="Close" onClick={onClose}>
              ×
            </button>
          </div>
        </div>
        {error && <div className="bnf-review-drillerror">{error}</div>}
        {data && (
          <div className="bnf-lens-check-warnings">
            {data.warnings.length === 0 ? (
              <span className="bb-green">No warnings — this file builds clean.</span>
            ) : (
              data.warnings.map((text) => (
                <div key={text} className="bnf-export-warning">
                  ⚠ {text}
                </div>
              ))
            )}
          </div>
        )}
        <div className="bnf-lens-check-body">
          <div className="bb-pdf-viewer bnf-sheet-viewer">
            {!data && loading && (
              <div className="bnf-sheet-loading">
                <span className="bnf-spin" aria-hidden="true" /> Building the file…
              </div>
            )}
            {data && (
              <>
                <Toolbar data={data} go={go} loading={loading} />
                <div className="bnf-sheet-scroll">
                  <SheetTable data={data} fmt={data.format} />
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
