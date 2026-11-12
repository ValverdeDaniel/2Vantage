import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { useDocuments } from '../../api/documents';
import { formatDate } from '../../lib/format';
import CoverageRow from './CoverageRow';
import CvgCheck from './CvgCheck';
import DocChip from './DocChip';
import DocPicker from './DocPicker';
import {
  cardState,
  gapWords,
  inForceState,
  isCollapsed,
  rememberCollapsed,
  shownKinds,
  tallyWords,
  yearColumns,
  yearState,
} from './coverageCard';
import useCoverageWrites from './useCoverageWrites';

/*
 * Coverage & marketing intent (plan.md §8.9; B16–B21, B23; old `CoverageIntentPanel.jsx` at 891f1b3, same classes):
 * what the client has today, and what we do with each line this year. Two controls per line — In force and This year
 * (Shop it · Keep as-is · Leave off) — written through intake's one door, which also writes the lines to quote;
 * tri-state select-all headers; the line, its state and note; Current plan; the documents each line needs; Confirm,
 * Confirm again and Reopen with ✓ Confirmed / ⚠ Changed since confirmed / Not confirmed yet. The body unmounts when
 * the card is put away, remembered per deal in this browser. The medical row's form pickers (B22) wait for slice 40.
 */
export default function CoverageIntentCard({ deal, meta, intent }) {
  const navigate = useNavigate();
  const writes = useCoverageWrites(deal.id);
  const documents = useDocuments(deal.id).data || [];
  const [open, setOpen] = useState(() => !isCollapsed(window.localStorage, deal.id));
  const [notes, setNotes] = useState({});
  const [guarantees, setGuarantees] = useState({});
  const [picking, setPicking] = useState(null); // {line, kind, el}
  const [anchor, setAnchor] = useState(null);
  const rows = intent.rows;
  const years = yearColumns(meta);
  const docKinds = meta?.intake?.coverage?.documents || [];
  const kindLabel = (kind) => docKinds.find((entry) => entry.kind === kind)?.label || kind;
  const state = cardState(intent);
  const gaps = gapWords(intent);
  const answered = rows.filter((row) => row.answered);
  const known = new Set(rows.map((row) => row.line));
  const addable = (meta?.lines || []).filter((line) => !known.has(line.key));
  const allLines = rows.map((row) => ({ key: row.line, label: row.label }));
  const busy = writes.busy;
  const colSpan = 5 + years.length;

  // The picker sits on the viewport: measured when it opens, and again on any scroll (the inner scroller too) or
  // resize, so it follows its chip.
  const syncAnchor = useCallback(() => setAnchor(picking?.el ? picking.el.getBoundingClientRect() : null), [picking]);
  const pick = (target) => {
    setPicking(target);
    setAnchor(target?.el ? target.el.getBoundingClientRect() : null);
  };
  useEffect(() => {
    if (!picking?.el) return undefined;
    window.addEventListener('scroll', syncAnchor, true);
    window.addEventListener('resize', syncAnchor);
    return () => {
      window.removeEventListener('scroll', syncAnchor, true);
      window.removeEventListener('resize', syncAnchor);
    };
  }, [picking, syncAnchor]);

  function toggleOpen() {
    const next = !open;
    setOpen(next);
    rememberCollapsed(window.localStorage, deal.id, !next);
    if (!next) pick(null);
  }

  const openInDocuments = (documentId) => navigate(`/deals/${deal.id}/documents?doc=${documentId}`);
  const inForce = inForceState(rows);

  function docsCell(row) {
    if (!row.answered) return <span className="bb-drop-meta">Needed if yes</span>;
    const kinds = shownKinds(
      row,
      docKinds.map((entry) => entry.kind),
    );
    if (!kinds.length) {
      return (
        <span className="bb-drop-meta" title="They do not have this line, so there is no renewal, invoice or SBC for it">
          —
        </span>
      );
    }
    return (
      <div className="bnf-cvg-docs">
        {kinds.map((kind) => {
          const ids = row.documents?.[kind] || [];
          const isOpen = picking?.line === row.line && picking?.kind === kind;
          return (
            <DocChip
              key={kind}
              kind={kind}
              label={kindLabel(kind)}
              ids={ids}
              open={isOpen}
              disabled={busy}
              onPick={(el) => pick(el ? { line: row.line, kind, el } : null)}
              onOpenDoc={openInDocuments}
              onDropFile={(file) => writes.uploadDocument(row.line, kind, kindLabel(kind), file)}
            >
              {isOpen && (
                <DocPicker
                  meta={meta}
                  line={row.line}
                  lineLabel={row.label}
                  kind={kind}
                  kindLabel={kindLabel(kind)}
                  attachedIds={ids}
                  documents={documents}
                  allLines={allLines}
                  busy={busy}
                  anchor={anchor}
                  onPatch={writes.patchDocument}
                  onUpload={(file) => writes.uploadDocument(row.line, kind, kindLabel(kind), file)}
                  onOpenDoc={openInDocuments}
                  onClose={() => pick(null)}
                />
              )}
            </DocChip>
          );
        })}
      </div>
    );
  }

  return (
    <div className={`bb-panel bnf-intake-section bnf-cvg ${state.cls}`}>
      <div className="bnf-cvg-head">
        <div>
          <div className="bb-panel-title">
            <button
              type="button"
              className="bnf-card-toggle"
              aria-expanded={open}
              aria-label={open ? 'Collapse Coverage & marketing intent' : 'Expand Coverage & marketing intent'}
              title={open ? 'Collapse this card' : 'Expand this card'}
              onClick={toggleOpen}
            >
              <span className={`bnf-req-chevron ${open ? 'expanded' : ''}`} aria-hidden="true">
                ▶
              </span>
            </button>
            Coverage &amp; marketing intent
          </div>
          {open && <div className="bb-panel-sub">{state.sub}</div>}
        </div>
        <div className="bnf-cvg-badges">
          {gaps.length > 0 && <span className="bnf-cvg-gapbadge">⚠ {gaps.join(' · ')}</span>}
          <span className="bnf-cvg-badge">{state.badge}</span>
        </div>
      </div>

      {open &&
        (rows.length === 0 ? (
          <div className="bb-empty">
            Nothing recorded yet — add the lines this client has today, and the ones we want to quote.
          </div>
        ) : (
          <div className="bb-grid-scroll bnf-cvg-scroll">
            <table className="bnf-cvg-table bnf-cvg-wide">
              <thead>
                <tr className="bnf-cvg-band">
                  <th className="bnf-cvg-linecell" />
                  <th />
                  <th />
                  <th />
                  <th className="bnf-cvg-bandlabel" colSpan={years.length}>
                    This year
                  </th>
                  <th />
                </tr>
                <tr className="bnf-cvg-colhead">
                  <th className="bnf-cvg-linecell">Line</th>
                  <th title="Has it today — the coverage currently in place">
                    <span className="bnf-cvg-th">In force</span>
                    <CvgCheck
                      state={inForce}
                      disabled={busy}
                      title={inForce === 'on' ? 'Mark every line as not in force' : 'Mark every line as in force'}
                      onClick={() => writes.applyAll(rows.map((row) => row.line), { has_today: inForce !== 'on' })}
                    />
                  </th>
                  <th>Current plan</th>
                  <th>Documents</th>
                  {years.map((column) => (
                    <th key={column.key}>
                      <span className="bnf-cvg-th">{column.label}</span>
                      <CvgCheck
                        state={yearState(rows, column.key)}
                        disabled={busy || !answered.length}
                        title={`Set every answered line to “${column.label}”`}
                        onClick={() =>
                          yearState(rows, column.key) !== 'on' &&
                          writes.applyAll(answered.map((row) => row.line), { this_year: column.key })
                        }
                      />
                    </th>
                  ))}
                  <th aria-label="Remove" />
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <CoverageRow
                    key={row.line}
                    row={row}
                    meta={meta}
                    years={years}
                    locked={busy}
                    busy={busy}
                    docs={docsCell(row)}
                    noteOpen={Boolean(notes[row.line])}
                    onNote={(value) => setNotes((current) => ({ ...current, [row.line]: value }))}
                    guarOpen={Boolean(guarantees[row.line])}
                    onGuar={(value) => setGuarantees((current) => ({ ...current, [row.line]: value }))}
                    onIntent={(patch) => writes.setIntent(row, patch)}
                    onPatch={(patch) => writes.patchLine(row, patch)}
                    colSpan={colSpan}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ))}

      {open && (
        <div className="bnf-cvg-foot">
          {addable.length > 0 && (
            <select
              className="bnf-intake-input bnf-w-narrow"
              value=""
              aria-label="Add a line"
              disabled={busy}
              onChange={(event) => event.target.value && writes.addLine(event.target.value)}
            >
              <option value="">＋ Add a line…</option>
              {addable.map((line) => (
                <option key={line.key} value={line.key}>
                  {line.label}
                </option>
              ))}
            </select>
          )}
          <span className="bb-drop-meta bnf-cvg-count">{tallyWords(intent)}</span>
          {intent.confirmed ? (
            <>
              <span className="bb-drop-meta">
                Confirmed {formatDate(intent.confirmed_at)}
                {intent.confirmed_by ? ` by ${intent.confirmed_by}` : ''}
              </span>
              <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={writes.reopen}>
                Reopen
              </button>
            </>
          ) : (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy || rows.length === 0}
              onClick={writes.confirm}
            >
              {intent.stale ? 'Confirm again' : 'Confirm coverage & intent'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
