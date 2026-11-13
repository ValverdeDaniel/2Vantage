import { useRef } from 'react';
import { downloadTemplate } from './portalApi';

/*
 * The files a link asks for (plan.md §8.20; L93, L94, L97; B22). Ported from old Vantage 891f1b3
 * `BenefitsClientPortal.jsx` ("Documents to upload", "Your employee census"): a drop card per slot, several files each,
 * staged here and sent one per request with Save progress or Submit (L97); "Received — <name>" for what came through
 * this request, with Replace. Files over the 30 MB cap are said at once, never sent (OQ24).
 *
 * staged: {slot: [File]} · onStage(slot, files) · onUnstage(slot, file) · onProblem(text) · readOnly
 */
const MAX_MB = 30;
const MAX_BYTES = MAX_MB * 1024 * 1024;

function Slot(props) {
  const { slot, label, detail, note, accept, received, icon, staged, onStage, onUnstage, onProblem, readOnly } = props;
  const receivedLabel = props.receivedLabel || label;
  const input = useRef(null);
  const files = staged[slot] || [];
  const pick = (event) => {
    const picked = [...(event.target.files || [])];
    const big = picked.find((file) => file.size > MAX_BYTES);
    if (big) onProblem(`${big.name} is over ${MAX_MB} MB: send a smaller copy, or split it into parts.`);
    const fits = picked.filter((file) => file.size <= MAX_BYTES);
    if (fits.length) onStage(slot, fits);
    event.target.value = '';
  };
  return (
    <div className="bnf-portal-doc-row">
      <input ref={input} type="file" accept={accept.join(',')} multiple style={{ display: 'none' }} disabled={readOnly}
             aria-label={`Upload ${label}`} onChange={pick} />
      {received.length > 0 && !files.length ? (
        // Wraps on a phone, and a long file name with it (the old row and badge never wrap; §8.20, slice 54).
        <div className="bnf-doc-row bnf-doc-received" style={{ flexWrap: 'wrap' }}>
          <span className="bnf-doc-icon">{icon}</span>
          <span className="bnf-doc-name">{receivedLabel}</span>
          <span className="bb-badge bb-badge-green" style={{ whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
            Received — {received.map((file) => file.name).join(', ')}
          </span>
          <button type="button" className="btn btn-secondary btn-sm" disabled={readOnly}
                  onClick={() => input.current?.click()}>
            Replace
          </button>
        </div>
      ) : (
        <div className="bb-drop-card" role="button" tabIndex={0} onClick={() => !readOnly && input.current?.click()}
             onKeyDown={(event) => event.key === 'Enter' && !readOnly && input.current?.click()}>
          <div className="bb-drop-icon">{icon}</div>
          {note && <div className="bnf-portal-doc-note">“{note}”</div>}
          {files.length ? (
            files.map((file) => (
              <div key={`${file.name}-${file.size}`} className="bb-drop-filename">
                {file.name}
                <span className="bb-drop-remove" title="Remove" role="button" tabIndex={0}
                      onClick={(event) => { event.stopPropagation(); onUnstage(slot, file); }}
                      onKeyDown={(event) => event.key === 'Enter' && onUnstage(slot, file)}>
                  ×
                </span>
              </div>
            ))
          ) : (
            <>
              <div className="bb-drop-filename">{label}</div>
              <div className="bb-drop-meta">{detail}</div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export function DocumentSlots({ documents, ...rest }) {
  if (!documents?.length) return null;
  return (
    <div className="bb-portal-card">
      <div className="bb-panel-title">Documents to upload</div>
      <div className="bb-panel-sub">Attach what’s still needed — anything we already have is marked received.</div>
      {documents.map((doc) => (
        <div key={doc.slot} id={`bnf-sec-doc_${doc.slot}`} data-ask-ref={`doc:${doc.slot}`}>
          <Slot slot={doc.slot} label={doc.label} detail={doc.detail} note={doc.note} accept={doc.accept}
                received={doc.received} icon="📄" {...rest} />
        </div>
      ))}
    </div>
  );
}

export function CensusFileCard({ token, censusFile, canTemplate, ...rest }) {
  if (!censusFile) return null;
  return (
    <div id="bnf-sec-census" className="bb-portal-card" data-ask-ref="census:file">
      <div className="bb-panel-title">Your employee census</div>
      <div className="bb-panel-sub">
        Any layout works — we normalize it on our side. Or start from our template if it is easier.
      </div>
      {canTemplate && (
        <div className="bnf-q-blankbar">
          <span className="bb-drop-meta">
            Don’t have a file to export? Use our template — it already lists every column we need for this group.
          </span>
          <button type="button" className="btn btn-secondary btn-sm"
                  onClick={() => downloadTemplate(token).catch(() => rest.onProblem('Could not download that file — please try again.'))}>
            ⬇ Download our census template
          </button>
        </div>
      )}
      <Slot slot="census_file" label="Attach your census file" receivedLabel="Employee census" detail={censusFile.detail} accept={censusFile.accept}
            received={censusFile.received} icon="🗂️" {...rest} />
    </div>
  );
}
