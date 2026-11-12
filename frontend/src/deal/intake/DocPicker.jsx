import { useRef } from 'react';
import { labelOf } from '../../api/meta';
import cx from '../../ui/cx';
import { attachChanges, coversEverything, toggleLineChanges } from './coverageCard';

/*
 * Which file covers this line: the popover behind a document chip (B21; old `CoverageDocPicker.jsx`, 891f1b3). It opens
 * from one row's chip and edits the file's whole scope, so one invoice can count for medical and dental in one visit.
 * A file's `lines` [] means every line ("nobody said"), shown as its own "Every line" toggle; a scoped file is never
 * ticked down to no lines. Picking a file of another kind re-files it and scopes it in one PATCH. It sits on the
 * viewport, re-measured by the card on scroll, because the card's scroller clips both axes.
 */
function popStyle(anchor) {
  if (!anchor) return {};
  const WIDTH = 380;
  const below = window.innerHeight - anchor.bottom - 16;
  const above = anchor.top - 16;
  const flip = below < 240 && above > below;
  return {
    position: 'fixed',
    left: Math.max(8, Math.min(anchor.left, window.innerWidth - WIDTH - 8)),
    width: WIDTH,
    maxHeight: Math.max(200, flip ? above : below),
    ...(flip ? { bottom: window.innerHeight - anchor.top + 4 } : { top: anchor.bottom + 4 }),
  };
}

export default function DocPicker({ meta, line, lineLabel, kind, kindLabel, attachedIds, documents, allLines, busy,
  anchor, onPatch, onUpload, onOpenDoc, onClose }) {
  const fileInput = useRef(null);
  const kinds = meta?.document_kinds || [];
  const kindName = (key) => labelOf(kinds, key);
  const accept = (kinds.find((entry) => entry.key === kind)?.accept || []).join(',');
  const attached = documents.filter((doc) => attachedIds.includes(doc.id));
  const others = documents.filter((doc) => !attachedIds.includes(doc.id));
  const sameKind = others.filter((doc) => doc.kind === kind);
  const rest = others.filter((doc) => doc.kind !== kind);
  const keys = allLines.map((entry) => entry.key);

  function attach(doc) {
    const changes = attachChanges(doc, line, kind);
    if (changes) onPatch(doc.id, changes);
    onClose(); // picking the file answers the chip's question
  }

  function toggle(doc, key) {
    const changes = toggleLineChanges(doc, key, keys);
    if (changes) onPatch(doc.id, changes);
  }

  const scopeRow = (doc) => {
    const every = coversEverything(doc);
    return (
      <div key={doc.id} className="bnf-cvgdoc-row">
        <div className="bnf-cvgdoc-name">
          <span title={doc.original_name}>{doc.display_name}</span>
          <span className="bb-drop-meta">{kindName(doc.kind)}</span>
        </div>
        <div className="bnf-cvgdoc-scope">
          <button
            type="button"
            className={cx('bnf-cvgdoc-all', every && 'is-on')}
            disabled={busy || every}
            title={every ? 'This file is not scoped to any line, so it counts for all of them' : 'Let it count for every line again'}
            onClick={() => onPatch(doc.id, { lines: [] })}
          >
            Every line
          </button>
          {allLines.map((entry) => {
            const on = every || (doc.lines || []).includes(entry.key);
            const last = !every && on && doc.lines.length === 1;
            const title = last
              ? 'A scoped file has to cover at least one line — switch it back to every line instead'
              : every
                ? `Scope it to the other lines, dropping ${entry.label}`
                : on
                  ? `Stop counting for ${entry.label}`
                  : `Also counts for ${entry.label}`;
            return (
              <button
                key={entry.key}
                type="button"
                className={cx('bnf-cvg-chip', on ? 'is-on' : 'is-off')}
                disabled={busy || last}
                title={title}
                onClick={() => toggle(doc, entry.key)}
              >
                {on ? '✓' : ''} {entry.label}
              </button>
            );
          })}
        </div>
        <button type="button" className="bnf-override-link" onClick={() => onOpenDoc(doc.id)}>
          Open in Documents →
        </button>
      </div>
    );
  };

  const pick = (doc, note, title) => (
    <button key={doc.id} type="button" className="bnf-cvgdoc-pick" disabled={busy} title={title} onClick={() => attach(doc)}>
      <span>{doc.display_name}</span>
      <span className="bb-drop-meta">{note}</span>
    </button>
  );

  return (
    <>
      <div className="bnf-cvgdoc-scrim" onClick={onClose} />
      <div className="bnf-cvgdoc-pop" role="dialog" aria-label={`${kindLabel} for ${lineLabel}`} style={popStyle(anchor)}>
        <div className="bnf-cvgdoc-head">
          <strong>
            {kindLabel} for {lineLabel}
          </strong>
          <button type="button" className="bnf-cvg-remove" aria-label="Close" onClick={onClose}>
            ×
          </button>
        </div>
        {attached.length > 0 ? (
          <div className="bnf-cvgdoc-sec">
            <div className="bnf-cvgdoc-secttl">On this line</div>
            {attached.map(scopeRow)}
          </div>
        ) : (
          <div className="bnf-cvgdoc-empty">
            No {kindLabel.toLowerCase()} on file for {lineLabel} yet.
          </div>
        )}
        {(sameKind.length > 0 || rest.length > 0) && (
          <div className="bnf-cvgdoc-sec">
            <div className="bnf-cvgdoc-secttl">{attached.length ? 'Use another file' : 'Pick the file'}</div>
            {sameKind.map((doc) =>
              pick(
                doc,
                coversEverything(doc)
                  ? `covers every line — scope it to ${lineLabel}?`
                  : `covers ${doc.lines.length} line${doc.lines.length === 1 ? '' : 's'}`,
              ),
            )}
            {rest.length > 0 && (
              <>
                <div className="bnf-cvgdoc-secttl is-sub">Something else on this deal</div>
                {rest.map((doc) =>
                  pick(
                    doc,
                    `${kindName(doc.kind)} → ${kindLabel}`,
                    `File it as the ${kindLabel.toLowerCase()} and scope it to ${lineLabel}`,
                  ),
                )}
              </>
            )}
          </div>
        )}
        <div className="bnf-cvgdoc-foot">
          <input
            ref={fileInput}
            type="file"
            hidden
            accept={accept}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = ''; // choosing the same file again fires again
              if (!file) return;
              onUpload(file);
              onClose();
            }}
          />
          <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => fileInput.current?.click()}>
            ⬆ Attach a {kindLabel.toLowerCase()}
          </button>
          <span className="bb-drop-meta">or drop a file on the chip</span>
        </div>
      </div>
    </>
  );
}
