import { lazy, Suspense } from 'react';
import { previewUrl, useFormCheck } from '../../api/questionnaire';

// pdf.js loads with the first preview, never with the form.
const PdfViewer = lazy(() => import('../../viewer/PdfViewer'));

/*
 * "Check the form ▸" (G67; the old FormCheck, words and classes kept): the filled PDF as it will download, in the
 * shared PDF pane, beside what is wrong with it. A preview is not a download: it sends no `ack` and is logged as a
 * view (G63).
 */
export default function FormCheck({ dealId, form, onClose }) {
  const check = useFormCheck(dealId, form);
  const problems = check.data?.problems || [];
  return (
    <div className="bnf-qcheck">
      <div className="bnf-qcheck-head">
        <b>Check the form</b>
        <span className="bnf-review-note">The filled PDF as it will download, beside what is wrong with it.</span>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onClose} title="Close the form check">
          Close
        </button>
      </div>
      <div className="bnf-qcheck-body">
        <div className="bnf-qcheck-pdf">
          <Suspense fallback={<div className="loading">Building the filled form…</div>}>
            <PdfViewer url={previewUrl(dealId, form)} />
          </Suspense>
        </div>
        <div className="bnf-qcheck-list">
          {check.isPending && <div className="loading">Checking…</div>}
          {check.isError && <div className="bnf-review-drillerror">The check could not be read.</div>}
          {check.data && !problems.length && (
            <div className="bnf-xcheck-row">
              <span className="bnf-xcheck-icon bnf-qcheck-ok">✓</span>
              <span className="bnf-xcheck-text">Nothing to fix on this form.</span>
            </div>
          )}
          {problems.map((problem) => (
            <div key={`${problem.code}:${problem.text}`} className="bnf-xcheck-row">
              <span className="bnf-xcheck-icon">⚠</span>
              <span className="bnf-xcheck-text">{problem.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
