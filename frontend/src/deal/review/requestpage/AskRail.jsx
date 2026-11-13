import { useState } from 'react';
import { askWords, chipWords, columnChips, REQUIRED, sectionsOf, STATUS_CLASSES } from './requestModel';

/*
 * The request page's ask list (plan.md §8.8; L29, L46; old 891f1b3 `RequestRail.jsx`): every section the client could
 * be asked about on this tab, in the order they meet them, each foldable, with "＋ Add all N" and a tick per question
 * (a census column: its blanks at once). A tick puts the item in the request tray; untick takes the draft out. Nothing
 * reaches them until the tray is sent. A click on a label opens the item's card (its thread, beside the list).
 * `readOnly` (a lost deal, a past year): statuses only.
 */
function Row({ item, labels, readOnly, busy, picked, onAsk, onRemove, onPick }) {
  const inCart = item.status === 'in_cart';
  const words = chipWords(item, labels);
  return (
    <div className={`rr-rail-q rr-rail-q-${item.status}${picked ? ' rr-rail-q-on' : ''}`}>
      <div className="rr-rail-qhead">
        <input
          type="checkbox"
          checked={inCart}
          aria-label={inCart ? `Take ${item.label} out of the tray` : `Ask for ${item.label}`}
          disabled={readOnly || busy || !(inCart || item.status === 'missing')}
          onChange={() => (inCart ? onRemove(item.draft_id) : onAsk([item.ref]))}
        />
        <button type="button" className="rr-rail-qlabel rr-rail-qpick" title="Open its card: the thread, and asking with a note" onClick={() => onPick(item.ref)}>
          {item.label}
          {item.needed && (
            <i className="rr-rail-req" title="Required">
              *
            </i>
          )}
        </button>
      </div>
      {(words || item.notes > 0) && (
        <div className="rr-rail-chips">
          {words && (
            <span className={`rr-rail-chip ${STATUS_CLASSES[item.status] || ''}`}>
              {words}
              {inCart && !readOnly && (
                <button type="button" className="rr-rail-x" disabled={busy} aria-label={`Take ${item.label} out of the tray`} title="Take it out of the tray" onClick={() => onRemove(item.draft_id)}>
                  ×
                </button>
              )}
            </span>
          )}
          {item.notes > 0 && <span className="rr-rail-chip">💬 {item.notes}</span>}
        </div>
      )}
    </div>
  );
}

function Section({ section, labels, readOnly, busy, picked, actions }) {
  const [open, setOpen] = useState(section.toAsk.length > 0 || section.items.some((item) => item.status !== 'on_file'));
  const n = section.toAsk.length;
  return (
    <div className={`rr-rail-sec${open ? ' rr-rail-sec-open' : ''}${section.key === REQUIRED ? ' rr-rail-required' : ''}`}>
      <div className="rr-rail-sechead">
        <button type="button" className="rr-rail-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
          <span className="rr-rail-caret" aria-hidden="true">
            {open ? '▾' : '▸'}
          </span>
          <b>{section.label}</b>
          <span className="rr-rail-count">{askWords(section)}</span>
        </button>
        {!readOnly && (
          <button
            type="button"
            className="rr-rail-addall"
            disabled={busy || !n}
            title={n ? `The ${n} blank question${n === 1 ? '' : 's'} here not in the tray or asked yet` : 'Nothing here is left to add: it is on file, in the tray or asked'}
            onClick={() => actions.onAsk(section.toAsk, { skip_out: true })}
          >
            ＋ Add all{n ? ` ${n}` : ''}
          </button>
        )}
      </div>
      {open && (
        <div className="rr-rail-body">
          {section.items.map((item) => (
            <Row key={item.ref} item={item} labels={labels} readOnly={readOnly} busy={busy} picked={picked === item.ref} {...actions} />
          ))}
        </div>
      )}
    </div>
  );
}

function ColumnRow({ column, readOnly, busy, onAskColumn }) {
  return (
    <div className="rr-rail-q">
      <label className="rr-rail-qhead">
        <input
          type="checkbox"
          checked={column.in_cart > 0}
          disabled={readOnly || busy || !column.blank || column.in_cart >= column.blank}
          aria-label={`Ask for every blank ${column.label}`}
          onChange={() => onAskColumn(column.key)}
        />
        <span className="rr-rail-qlabel">
          {column.label}
          {column.required && (
            <i className="rr-rail-req" title="Required">
              *
            </i>
          )}
        </span>
      </label>
      <div className="rr-rail-chips">
        {columnChips(column).map(([words, cls]) => (
          <span key={words} className={`rr-rail-chip ${cls}`}>
            {words}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function AskRail({ page, items, labels, readOnly, busy, picked, actions }) {
  const sections = sectionsOf(items);
  return (
    <div className="rr-rail" aria-label="What to ask">
      <div className="rr-rail-titlerow">
        <div className="rr-rail-title">Ask</div>
      </div>
      <div className="rr-rail-sub">
        {readOnly ? 'This deal asks its client nothing now: the list only reads.' : 'Tick what to ask: it waits in the request tray, and nothing reaches them until you send it.'}
      </div>
      {sections.map((section) => (
        <Section key={section.key} section={section} labels={labels} readOnly={readOnly} busy={busy} picked={picked} actions={actions} />
      ))}
      {page.columns && (
        <div className="rr-rail-sec rr-rail-sec-open">
          <div className="rr-rail-sechead">
            <span className="rr-rail-toggle rr-rail-toggle-still">
              <b>Census values</b>
              <span className="rr-rail-count">a column at a time</span>
            </span>
          </div>
          <div className="rr-rail-body">
            {page.columns.map((column) => (
              <ColumnRow key={column.key} column={column} readOnly={readOnly} busy={busy} onAskColumn={actions.onAskColumn} />
            ))}
          </div>
        </div>
      )}
      {!sections.length && !page.columns && <div className="rr-rail-note">Nothing to ask on this tab.</div>}
    </div>
  );
}
