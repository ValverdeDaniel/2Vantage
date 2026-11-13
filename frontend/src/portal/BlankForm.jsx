import { lazy, Suspense, useEffect, useState } from 'react';
import { getFormBlank } from './portalApi';

const PdfViewer = lazy(() => import('../viewer/PdfViewer'));

/*
 * "View the official carrier form ▸" and "⬇ Download blank PDF" over a form (plan.md §8.20; G84; slice 58). Ported
 * from old Vantage 891f1b3 `BenefitsClientPortal.jsx` (`bnf-q-blankbar`, `ClientBlankPdf`): the blank is fetched
 * through the link (its PIN proof rides along) and shown on the page in the shared PDF viewer. A preview has no token,
 * so both stay off there (old `embedded`).
 */
function Inline({ token, form, onProblem }) {
  const [bytes, setBytes] = useState(null);
  useEffect(() => {
    let alive = true;
    getFormBlank(token, form)
      .then((data) => alive && setBytes(data))
      .catch(() => alive && onProblem('Could not open the carrier form — please try again.'));
    return () => {
      alive = false;
    };
  }, [token, form, onProblem]);
  if (!bytes) return <div className="loading">Loading the carrier form…</div>;
  return (
    <Suspense fallback={<div className="loading">Loading the carrier form…</div>}>
      <PdfViewer data={bytes} />
    </Suspense>
  );
}

export default function BlankForm({ token, form, onProblem }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <div className="bnf-q-blankbar" style={{ flexWrap: 'wrap' }}>
        <button type="button" className="btn btn-secondary btn-sm" disabled={!token} onClick={() => setOpen(!open)}>
          {open ? 'Hide the official carrier form' : 'View the official carrier form ▸'}
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={!token}
          onClick={() => getFormBlank(token, form, { save: true }).catch(() => onProblem('Could not download that file — please try again.'))}
        >
          ⬇ Download blank PDF
        </button>
      </div>
      {open && (
        <div className="bnf-q-blank">
          <Inline token={token} form={form} onProblem={onProblem} />
        </div>
      )}
    </>
  );
}
