import { useRef } from 'react';

const MAX_MB = 30;

/*
 * "Already filled this out on paper?" (plan.md §8.20; G90, G92; slice 58). Ported from old Vantage 891f1b3
 * `BenefitsClientPortal.jsx` (`bnf-q-upload`): the completed form attached here waits ("attached — save to send ×")
 * and goes with Save or Submit like every file on the page (L97); what came through this request reads "Received —
 * <name>" with Replace. It is filed for the team to review (G90: no read on the link; the old auto-scan, G91, is not
 * built). A form asked only as a signed copy says so in its own words.
 *
 * file: {slot, accept, received} · staged / onStage / onUnstage / onProblem / readOnly: the page's files (FileSlots)
 */
export default function QuestionnairePaper({ file, copyOnly, staged, onStage, onUnstage, onProblem, readOnly }) {
  const input = useRef(null);
  const waiting = (staged || {})[file.slot] || [];
  const pick = (event) => {
    const picked = event.target.files?.[0];
    event.target.value = '';
    if (!picked) return;
    if (picked.size > MAX_MB * 1024 * 1024) {
      onProblem(`${picked.name} is over ${MAX_MB} MB: send a smaller copy.`);
      return;
    }
    waiting.forEach((one) => onUnstage(file.slot, one));
    onStage(file.slot, [picked]);
  };
  const received = file.received || [];
  return (
    <div className="bnf-q-upload">
      <div className="bnf-q-upload-title">{copyOnly ? 'Your signed copy' : 'Already filled this out on paper?'}</div>
      <p className="bnf-q-intro">
        {copyOnly
          ? 'Fill out the carrier’s form, sign it, and attach the signed copy here — our team will review it.'
          : 'Upload the completed form — our team will review it.'}
      </p>
      <input ref={input} type="file" accept={file.accept.join(',')} style={{ display: 'none' }} disabled={readOnly}
             aria-label="Attach the completed form" onChange={pick} />
      {waiting.length > 0 ? (
        <div className="bnf-doc-row" style={{ flexWrap: 'wrap' }}>
          <span className="bb-badge bb-badge-green" style={{ whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
            {waiting[0].name}
          </span>
          <span className="bnf-q-staged-note">attached — save to send</span>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => onUnstage(file.slot, waiting[0])}>
            ×
          </button>
        </div>
      ) : received.length > 0 ? (
        <div className="bnf-doc-row" style={{ flexWrap: 'wrap' }}>
          <span className="bb-badge bb-badge-green" style={{ whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
            Received — {received[received.length - 1].name}
          </span>
          <button type="button" className="btn btn-secondary btn-sm" disabled={readOnly}
                  onClick={() => input.current?.click()}>
            Replace
          </button>
        </div>
      ) : (
        <button type="button" className="btn btn-secondary btn-sm" disabled={readOnly}
                onClick={() => input.current?.click()}>
          Attach completed form
        </button>
      )}
    </div>
  );
}
