import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { useModalLayer } from '../../ui/useModalLayer';

const SILENT = 'nothing is dropped silently.';

/*
 * "Before you download: …" (G65; the old ExportCheckModal, words and classes kept): what is wrong with the file, each
 * with Fix ▸, then "Not now" or "Download (anyway) ⬇". Nothing blocks. After a stale `ack` the fresh report shows with
 * "Something changed since you opened this." (G66). Escape and the backdrop close it.
 */
export default function CheckModal({ state, onClose, onDownload, onFix }) {
  const ref = useRef(null);
  useModalLayer(ref, { onEscape: onClose });
  const { request, report, loading, busy, error, stale } = state;
  const problems = report?.problems || [];
  const count = problems.length;
  let sub = 'All checks passed.';
  if (loading) sub = 'Checking the file…';
  else if (count) sub = `${count} thing${count === 1 ? '' : 's'} to know before it goes out — ${SILENT}`;
  let action = count ? 'Download anyway ⬇' : 'Download ⬇';
  if (busy) action = 'Building…';
  return createPortal(
    <div
      className="progress-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div ref={ref} role="dialog" aria-modal="true" aria-label="Before you download" className="bb-modal bnf-xcheck">
        <div className="bb-modal-header">
          <div>
            <div className="bb-modal-title">Before you download: {report?.label || request.label}</div>
            <div className="bb-modal-sub">{sub}</div>
          </div>
          <button type="button" className="btn-close" aria-label="Close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="bnf-export-warnings">
          {stale && (
            <div className="bnf-xcheck-stale">
              Something changed since you opened this. Here is the check as it stands now.
            </div>
          )}
          {loading && <div className="loading">Checking…</div>}
          {!loading && !count && !error && (
            <div className="bnf-export-ok">✓ Nothing to fix: the file is ready to go.</div>
          )}
          {problems.map((problem) => (
            <div key={`${problem.code}:${problem.text}`} className="bnf-xcheck-row">
              <span className="bnf-xcheck-icon">⚠</span>
              <div className="bnf-xcheck-text">{problem.text}</div>
              {problem.fix && onFix && (
                <button type="button" className="bnf-override-link" onClick={() => onFix(problem.fix)}>
                  Fix ▸
                </button>
              )}
            </div>
          ))}
          {error && (
            <div role="alert" className="bnf-review-drillerror">
              {error}
            </div>
          )}
        </div>
        <div className="bb-modal-footer bnf-xcheck-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Not now
          </button>
          <button type="button" className="btn btn-primary" disabled={loading || busy || !report} onClick={onDownload}>
            {action}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
