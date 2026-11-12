import { useState } from 'react';
import { formatDate } from '../../lib/format';
import ChecklistRow from './ChecklistRow';
import FormPicker from './FormPicker';
import { isCollapsed, meterOf, rememberCollapsed, subtitleOf } from './checklistModel';
import useChecklistWrites from './useChecklistWrites';

// The two rows that carry an in-app form's picker (B22; the questionnaire's, slice 42).
const FORM_ITEMS = new Set(['medical_questionnaire', 'stop_loss_disclosure']);

/*
 * The Marketing readiness checklist (plan.md §8.9; B25–B28), the old card (891f1b3 `MarketingChecklist.jsx`, same
 * classes): the size tier and enrolled headcount, the "N/M ready" meter, "Sent to market <date>" once marketed (still
 * editable), and the rows. One card for every door (B28): the Intake tab mounts it here; the RFP tab and the Overview
 * mount it from this folder's index, and may own its open state (`open`, `onToggleOpen`) and hand in their own mark
 * (`mark`), as the old RFP door did. Put away per deal in this browser, under the old card's key.
 */
export default function ChecklistCard({ deal, meta, checklist, sentAt, open: openHere, onToggleOpen, mark = null }) {
  const writes = useChecklistWrites(deal.id);
  const [openState, setOpen] = useState(() => !isCollapsed(window.localStorage, deal.id));
  const controlled = openHere !== undefined;
  const open = controlled ? openHere : openState;
  if (!checklist) return null;
  const meter = meterOf(checklist);
  const acceptOf = (kind) => (meta?.document_kinds || []).find((entry) => entry.key === kind)?.accept?.join(',') || '';

  function toggleOpen() {
    const next = !open;
    if (controlled) onToggleOpen(next);
    else {
      setOpen(next);
      rememberCollapsed(window.localStorage, deal.id, !next);
    }
  }

  const meterBox = (
    <div className="bnf-meter bnf-marketing-meter">
      <div className="bnf-meter-head">
        <span className="bnf-meter-label">
          {meter.done}/{meter.required} ready
        </span>
        <span className={`bnf-meter-pct bb-mono ${meter.cls}`}>{meter.pct}%</span>
      </div>
      <div className="bb-readiness-track">
        <div className={`bb-readiness-fill ${meter.cls}-bg`} style={{ width: `${meter.pct}%` }} />
      </div>
    </div>
  );

  return (
    <div className="bb-panel bnf-marketing-panel">
      <div className="bnf-marketing-head">
        <div>
          <div className="bb-panel-title">
            <button
              type="button"
              className="bnf-card-toggle"
              aria-expanded={open}
              aria-label={open ? 'Collapse Marketing readiness checklist' : 'Expand Marketing readiness checklist'}
              title={open ? 'Collapse this card' : 'Expand this card'}
              onClick={toggleOpen}
            >
              <span className={`bnf-req-chevron ${open ? 'expanded' : ''}`} aria-hidden="true">
                ▶
              </span>
            </button>
            Marketing readiness checklist
          </div>
          {open && <div className="bb-panel-sub">{subtitleOf(checklist, sentAt)}</div>}
          {sentAt && <span className="bb-badge bb-badge-muted bnf-marketing-sent">Sent to market {formatDate(sentAt)}</span>}
        </div>
        {mark ? (
          <div className="bnf-marketing-side">
            {mark}
            {meterBox}
          </div>
        ) : (
          meterBox
        )}
      </div>
      {open && (
        <div className="bnf-marketing-items">
          {checklist.items.map((item) => (
            <ChecklistRow
              key={item.key}
              item={item}
              accept={acceptOf(item.kind)}
              busy={writes.busy}
              onTick={writes.tick}
              onRequirement={writes.requirement}
              onAttach={writes.attach}
            >
              {FORM_ITEMS.has(item.key) && <FormPicker deal={deal} meta={meta} item={item} />}
            </ChecklistRow>
          ))}
        </div>
      )}
    </div>
  );
}
