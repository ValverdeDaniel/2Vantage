import { useColumnDrill } from '../../../api/reviewForm';
import { labelIn } from '../reviewModel';
import { barTitle, peopleWord } from './boardModel';
import { OriginDot } from './BoardFilters';

const TONES = {
  identity: 'bnf-review-tone-person',
  demographics: 'bnf-review-tone-person',
  employment: 'bnf-review-tone-work',
  medical: 'bnf-review-tone-med',
};

/*
 * One row of the Census board: one census COLUMN (plan.md §8.8; C27, C28; old 891f1b3 `CensusReviewFieldRow.jsx`). The
 * person axis is a stacked bar plus a number line, never a square per person: five nodes, whatever the roster's size.
 * Its tick asks the client for the column's blanks (into the request tray); its label carries its help; the band, filled
 * / total, the five-segment bar, where the filled values came from, "differ from what the client sent", ▸ who / values
 * (the drill, C28) and Auto · Required · Waived. The assignee picker is gone with partition mode (L47, L67; OQ88).
 */
export default function CensusColumnRow({ dealId, column, meta, picked, expanded, busy, readOnly, onPick, onRule, onDrill }) {
  const waived = column.rule === 'waived';
  const blocked = waived ? 'Waived on this deal.' : !column.askable ? 'Nothing left to ask for.' : '';
  const gaps = column.counts.missing + column.counts.na;
  const cls = [
    'bnf-review-row',
    column.required && column.counts.missing ? 'bnf-review-row-required' : '',
    gaps === 0 ? 'bnf-review-row-complete' : '',
    !column.quoted ? 'bnf-review-row-out' : '',
    waived ? 'bnf-review-row-waived' : '',
  ].filter(Boolean).join(' ');
  return (
    <>
      <div className={cls}>
        <div className="bnf-review-checkcell">
          <input type="checkbox" checked={picked} disabled={readOnly || Boolean(blocked)} aria-label={`Ask for ${column.label}`}
            title={blocked || 'Ask the client for this column’s blanks'} onChange={() => onPick(column)} />
        </div>
        <div className="bnf-review-fieldcell">
          <div className="bnf-review-fieldlabel">
            {column.label}
            {column.rule === 'required' && <span className="bnf-review-chip-req">Required</span>}
            {waived && <span className="bnf-review-chip-waived">Waived</span>}
            {!column.quoted && <span className="bnf-review-chip-line">Line not quoted</span>}
          </div>
          <div className="bnf-review-fieldsub">{column.help || labelIn(meta?.census_groups, column.group)}</div>
        </div>
        <div className={`bnf-review-bandcell ${TONES[column.group] || 'bnf-review-tone-anc'}`}>{labelIn(meta?.census_groups, column.group)}</div>
        <div className="bnf-review-fill">
          {waived ? (
            <span className="bnf-review-fill-waived">— of {column.total}</span>
          ) : (
            <>
              <b>{column.filled}</b>
              <span className="bnf-review-fill-sep">/</span>
              {column.total}
              <span className="bnf-review-fill-unit"> {peopleWord(column)}</span>
            </>
          )}
        </div>
        <div className="bnf-review-spread">
          <div className="bnf-review-stack" title={barTitle(column, meta?.census_segments)}>
            {(meta?.census_segments || []).map((segment) =>
              column.counts[segment.key] ? (
                <span key={segment.key} className={`bnf-review-seg bnf-review-seg-${segment.key}`} style={{ flex: column.counts[segment.key] }}
                  title={`${column.counts[segment.key]} · ${segment.label}`} />
              ) : null,
            )}
          </div>
          <div className="bnf-review-counts">
            {column.counts.missing > 0 && <b>{column.counts.missing} missing</b>}
            {column.counts.low > 0 && <> · {column.counts.low} to review</>}
            {column.counts.client > 0 && <> · {column.counts.client} from client</>}
            {column.counts.missing === 0 && column.counts.na > 0 && <>{column.counts.na} not required here</>}
            {column.asked > 0 && <> · {column.asked} asked</>}
            {column.in_cart > 0 && <> · {column.in_cart} in the tray</>}
          </div>
          {Object.keys(column.origins).length > 0 && (
            <div className="bnf-review-origins">
              {(meta?.origins || []).filter((origin) => column.origins[origin.key]).map((origin) => (
                <span key={origin.key} className="rr-origin-legend-item" title={origin.label}>
                  <OriginDot origin={origin} /> {column.origins[origin.key]} {origin.short}
                </span>
              ))}
            </div>
          )}
          {column.differs > 0 && (
            <span className="rr-differs-chip" title="The client sent a different value from the one we hold — open the values to compare">
              {column.differs} differ from what the client sent
            </span>
          )}
          {(gaps > 0 || column.filled > 0) && (
            <button type="button" className="bnf-review-drill" aria-expanded={expanded} onClick={() => onDrill(column)}>
              {expanded ? '▾ hide' : gaps > 0 ? `▸ who (${gaps})` : `▸ values (${column.filled})`}
            </button>
          )}
        </div>
        <div className="bnf-review-reqtoggle">
          {(meta?.rules || []).map((choice) => (
            <button key={choice.key} type="button" disabled={busy || (choice.key === 'required' && column.key === 'ssn')}
              className={`bnf-review-reqbtn${choice.key === 'waived' ? ' bnf-review-reqbtn-waived' : ''}${column.rule === choice.key ? ' bnf-review-reqbtn-on' : ''}`}
              onClick={() => column.rule !== choice.key && onRule(column, choice.key)}>
              {choice.label}
            </button>
          ))}
        </div>
      </div>
      {expanded && <ColumnDrill dealId={dealId} column={column} meta={meta} />}
    </>
  );
}

/* C28: who is blank, and each value with where it came from beside what the client sent. */
function ColumnDrill({ dealId, column, meta }) {
  const drill = useColumnDrill(dealId, column.key);
  if (drill.isPending) return <div className="bnf-review-drillrow bnf-review-note">Loading the people…</div>;
  if (drill.isError) return <div className="bnf-review-drillerror">Could not load the people for this column.</div>;
  return (
    <div className="bnf-review-values">
      <div className="bnf-review-values-head bnf-review-note">{column.label}: each person, what we hold and where it came from</div>
      {drill.data.people.map((row) => (
        <div key={row.ref} className="bnf-review-valuerow">
          <span className={`bnf-review-person${row.kind === 'dependent' ? ' bnf-review-person-dep' : ''}`}>{row.title}</span>
          <span className="bnf-review-value">{row.value || (row.missing ? <b>Missing</b> : <span className="bb-muted">Blank</span>)}</span>
          {row.origin && <span className="bnf-review-note">{labelIn(meta?.origins, row.origin)}</span>}
          {row.theirs && <span className={row.differs ? 'rr-differs-chip' : 'bnf-review-note'}>Client sent: {row.theirs}</span>}
          {row.asked && <span className="bnf-review-note">Asked</span>}
          {row.in_cart && <span className="bnf-review-note">In the tray</span>}
        </div>
      ))}
    </div>
  );
}
