import { useState } from 'react';
import ConfirmDialog from '../../../ui/ConfirmDialog';
import { confirmQuestion, docMeta, ignoreCount, plural } from './confidenceWords';

/**
 * The files the deal's values came from (plan.md §8.6; M87–M89; old Vantage 891f1b3 `DataConfidence.jsx`): each with
 * its quality chip (the review rules' headline), "N values · M confirmed", **Confirm all** while any is unconfirmed —
 * which asks first (M88) and confirms every value read from the file on every owner, census included — and, while
 * the file has open warnings not flagged, **Ignore N warnings** and **⚑ Needs checking**. Each is one review with its
 * Undo (`useConfidenceMarks`).
 */
export default function DocumentRows({ documents, more, busy, onReview }) {
  const [asking, setAsking] = useState(null);
  if (!documents.length) return null;
  const confirm = () => {
    const doc = asking;
    setAsking(null);
    onReview(doc, 'approve');
  };
  return (
    <div className="bnf-ov-conf-docs">
      {documents.map((doc) => {
        const ignore = ignoreCount(doc);
        return (
          <div key={doc.id} className="bnf-ov-conf-doc">
            <div className="bnf-ov-conf-docmain">
              <span className="bnf-doc-name">{doc.name}</span>
              <span className={`bnf-quality-label bb-${doc.headline.tone}`}>{doc.headline.label}</span>
            </div>
            <div className="bnf-ov-conf-docmeta">
              <span className="bb-drop-meta">{docMeta(doc)}</span>
              {doc.confirmed < doc.values && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={!!busy}
                  onClick={() => setAsking(doc)}
                >
                  {busy === `approve:${doc.id}` ? 'Confirming…' : 'Confirm all'}
                </button>
              )}
              {ignore > 0 && (
                <>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={!!busy}
                    title="Leave this file's flagged values as read and stop warning about them — listed below with Undo"
                    onClick={() => onReview(doc, 'ignore')}
                  >
                    {busy === `ignore:${doc.id}` ? 'Ignoring…' : `Ignore ${plural(ignore, 'warning')}`}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm bnf-review-btn-check"
                    disabled={!!busy}
                    title="Flag this file's warnings for a second look"
                    onClick={() => onReview(doc, 'check')}
                  >
                    {busy === `check:${doc.id}` ? 'Flagging…' : '⚑ Needs checking'}
                  </button>
                </>
              )}
            </div>
          </div>
        );
      })}
      {more > 0 && <div className="bb-drop-meta">and {plural(more, 'more file')} — the files with most values shown</div>}
      <ConfirmDialog
        open={!!asking}
        title={asking ? confirmQuestion(asking) : 'Confirm all'}
        message="Each value read from it is marked as checked by you, wherever it lives. Undo puts them back."
        confirmLabel="Confirm all"
        onConfirm={confirm}
        onCancel={() => setAsking(null)}
      />
    </div>
  );
}
