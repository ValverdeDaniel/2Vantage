import { useConfidence } from '../../../api/confidence';
import InlineError from '../../../ui/InlineError';
import DocumentRows from './DocumentRows';
import MarkedList from './MarkedList';
import RecheckPanel from './RecheckPanel';
import useConfidenceMarks from './useConfidenceMarks';

/**
 * Data confidence (plan.md §8.6; M83–M93; M.6; old Vantage 891f1b3 `DataConfidence.jsx`), the last side card of the
 * Overview: where each value came from — Scanned (with those corrected by hand), Typed, From the client (with those
 * awaiting approval) — and whether it has been checked: the Confirmed bar and its legend (by a person, by the re-read,
 * low-confidence, to review, need checking, ignored), the files with their quality and buttons (`DocumentRows`), the
 * record of what was ignored or flagged (`MarkedList`, each with Undo) and the AI re-read (`RecheckPanel`). Provenance
 * and confirmation are never conflated. Every count is review's (`GET deals/{id}/confidence/`), and every button one
 * review across the owners with its Undo.
 */
export default function ConfidenceCard({ dealId }) {
  const confidence = useConfidence(dealId);
  const marks = useConfidenceMarks(dealId);
  const data = confidence.data;
  if (confidence.isError) {
    return (
      <div className="bb-panel bnf-ov-confidence">
        <InlineError
          title="Could not load the data confidence."
          error={confidence.error}
          onRetry={() => confidence.refetch()}
          retrying={confidence.isFetching}
        />
      </div>
    );
  }
  if (!data) return null;
  const { cells, confirmed, warnings } = data;
  const byFile = (doc, action) => marks.run(`${action}:${doc.id}`, { action, documentId: doc.id }, doc.name);
  const byRow = (row, action) => marks.run(`${action}:${row.ref}`, { action, refs: [row.ref] });
  const undoAll = () => marks.run('undo-all', { action: 'clear', refs: data.ignored.rows.map((row) => row.ref) });

  return (
    <div className="bb-panel bnf-ov-confidence">
      <div className="bb-panel-title">Data confidence</div>
      <div className="bb-panel-sub">Where each value came from, and whether it has been checked.</div>
      <div className="bnf-ov-conf-split">
        <div className="bnf-ov-conf-cell">
          <div className="bnf-ov-conf-value bb-mono">{cells.scanned}</div>
          <div className="bnf-ov-conf-label">Scanned</div>
          {cells.corrected > 0 && <div className="bb-drop-meta">{cells.corrected} corrected by hand</div>}
        </div>
        <div className="bnf-ov-conf-cell">
          <div className="bnf-ov-conf-value bb-mono">{cells.typed}</div>
          <div className="bnf-ov-conf-label">Typed</div>
        </div>
        <div className="bnf-ov-conf-cell">
          <div className="bnf-ov-conf-value bb-mono">{cells.from_client}</div>
          <div className="bnf-ov-conf-label">From the client</div>
          {cells.pending > 0 && <div className="bb-drop-meta">{cells.pending} awaiting approval</div>}
        </div>
      </div>
      <div className="bnf-progress-row bnf-ov-conf-bar">
        <span className="bnf-progress-label">Confirmed</span>
        <span className="bnf-progress-count bb-mono">
          {confirmed.total}/{data.filled} · {confirmed.pct}%
        </span>
      </div>
      <div className="bnf-progress-track">
        <div className="bnf-progress-fill" style={{ width: `${confirmed.pct}%` }} />
      </div>
      <div className="bnf-ov-conf-legend">
        <span>
          <span className="bnf-ov-key bnf-ov-key-user" /> {confirmed.by_person} by a person
        </span>
        <span>
          <span className="bnf-ov-key bnf-ov-key-auto" /> {confirmed.by_recheck} by the re-read
        </span>
        {warnings.low > 0 && <span className="bb-amber">{warnings.low} low-confidence</span>}
        {warnings.to_review > 0 && <span className="bb-amber">{warnings.to_review} to review</span>}
        {warnings.check > 0 && <span className="bb-rose">⚑ {warnings.check} need checking</span>}
        {warnings.ignored > 0 && <span className="bb-drop-meta">{warnings.ignored} ignored</span>}
      </div>
      <DocumentRows documents={data.documents} more={data.documents_more} busy={marks.busy} onReview={byFile} />
      <MarkedList
        title="Ignored"
        dealId={dealId}
        list={data.ignored}
        total={warnings.ignored}
        busy={marks.busy}
        actions={[{ action: 'clear', label: 'Undo' }]}
        onAction={byRow}
        headAction={
          <button type="button" className="bnf-override-link" disabled={!!marks.busy} onClick={undoAll}>
            Undo all
          </button>
        }
      />
      <MarkedList
        title="Needs checking"
        dealId={dealId}
        list={data.check}
        total={warnings.check}
        busy={marks.busy}
        actions={[
          { action: 'approve', label: '✓ Approve' },
          { action: 'clear', label: 'Undo' },
        ]}
        onAction={byRow}
      />
      <RecheckPanel dealId={dealId} recheck={data.recheck} />
    </div>
  );
}
