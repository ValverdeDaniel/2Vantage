import { useState } from 'react';
import { askWords, chipWords, columnChips, REQUIRED, sectionsOf, STATUS_CLASSES } from './requestModel';

/*
 * The request page's ask list (plan.md §8.8; L29, L42, L46; old 891f1b3 `RequestRail.jsx`): every section the client
 * could be asked about on this tab, in the order they meet them, each foldable, with "＋ Add all N" and a tick per
 * question (a census column: its blanks at once). With All people a tick puts the item in the request tray; untick
 * takes the draft out. On a person's link (the Ask card, slice 57) the page hands in `mode`: what each tick says on
 * THAT link ("On their link", "Will be added", "Coming off"), what a tick does, the part switches above (`top`) and
 * Update link below (`foot`). A click on a label opens the item's card. `readOnly` (a lost deal, a past year): statuses
 * only.
 */
function trayTick(item, labels) {
  const inCart = item.status === 'in_cart';
  return {
    checked: inCart,
    enabled: inCart || item.status === 'missing',
    chip: chipWords(item, labels),
    cls: STATUS_CLASSES[item.status] || '',
    undo: inCart ? item.draft_id : null,
  };
}

function Row({ item, labels, mode, readOnly, busy, picked, actions }) {
  const tick = mode ? mode.tickOf(item) : trayTick(item, labels);
  const onTick = () => (mode ? mode.onTick(item) : tick.checked ? actions.onRemove(item.draft_id) : actions.onAsk([item.ref]));
  return (
    <div className={`rr-rail-q rr-rail-q-${item.status}${picked ? ' rr-rail-q-on' : ''}`} data-ask-ref={item.ref}
      onDoubleClick={() => actions.onEdit?.(item)}>
      <div className="rr-rail-qhead">
        <input type="checkbox" checked={tick.checked} disabled={readOnly || busy || !tick.enabled}
          aria-label={tick.checked ? `Take ${item.label} off` : `Ask for ${item.label}`} onChange={onTick} />
        <button type="button" className="rr-rail-qlabel rr-rail-qpick" title="Open its card: the thread, and asking with a note" onClick={() => actions.onPick(item.ref)}>
          {item.label}
          {item.needed && (
            <i className="rr-rail-req" title="Required">
              *
            </i>
          )}
        </button>
      </div>
      {(tick.chip || item.notes > 0) && (
        <div className="rr-rail-chips">
          {tick.chip && (
            <span className={`rr-rail-chip ${tick.cls}`}>
              {tick.chip}
              {tick.undo && !readOnly && (
                <button type="button" className="rr-rail-x" disabled={busy} aria-label={`Take ${item.label} out of the tray`} title="Take it out of the tray" onClick={() => actions.onRemove(tick.undo)}>
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

function Section({ section, labels, mode, readOnly, busy, picked, actions }) {
  const toAsk = mode ? mode.toAsk(section) : section.toAsk;
  const [open, setOpen] = useState(toAsk.length > 0 || section.items.some((item) => item.status !== 'on_file'));
  const n = toAsk.length;
  return (
    <div className={`rr-rail-sec${open ? ' rr-rail-sec-open' : ''}${section.key === REQUIRED ? ' rr-rail-required' : ''}`}>
      <div className="rr-rail-sechead">
        <button type="button" className="rr-rail-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
          <span className="rr-rail-caret" aria-hidden="true">
            {open ? '▾' : '▸'}
          </span>
          <b>{section.label}</b>
          <span className="rr-rail-count">{askWords({ ...section, toAsk })}</span>
        </button>
        {!readOnly && (
          <button type="button" className="rr-rail-addall" disabled={busy || !n}
            title={n ? `The ${n} blank question${n === 1 ? '' : 's'} here not ticked or asked yet` : 'Nothing here is left to add: it is on file, ticked or asked'}
            onClick={() => (mode ? mode.addAll(toAsk) : actions.onAsk(toAsk, { skip_out: true }))}>
            ＋ Add all{n ? ` ${n}` : ''}
          </button>
        )}
      </div>
      {open && (
        <div className="rr-rail-body">
          {section.items.map((item) => (
            <Row key={item.ref} item={item} labels={labels} mode={mode} readOnly={readOnly} busy={busy} picked={picked === item.ref} actions={actions} />
          ))}
        </div>
      )}
    </div>
  );
}

function ColumnRow({ column, mode, readOnly, busy, onAskColumn }) {
  const tick = mode?.columnTickOf
    ? mode.columnTickOf(column)
    : { checked: column.in_cart > 0, enabled: Boolean(column.blank) && column.in_cart < column.blank, chips: columnChips(column) };
  return (
    <div className="rr-rail-q">
      <label className="rr-rail-qhead">
        <input type="checkbox" checked={tick.checked} disabled={readOnly || busy || !tick.enabled} aria-label={`Ask for every blank ${column.label}`}
          onChange={() => (mode?.onColumnTick ? mode.onColumnTick(column) : onAskColumn(column.key))} />
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
        {tick.chips.map(([words, cls]) => (
          <span key={words} className={`rr-rail-chip ${cls}`}>
            {words}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function AskRail({ page, items, labels, readOnly, busy, picked, actions, mode = null }) {
  const sections = sectionsOf(items);
  return (
    <div className="rr-rail" aria-label="What to ask">
      <div className="rr-rail-titlerow">
        <div className="rr-rail-title">{mode?.title || 'Ask'}</div>
      </div>
      <div className="rr-rail-sub">
        {readOnly
          ? 'This deal asks its client nothing now: the list only reads.'
          : mode?.sub || 'Tick what to ask: it waits in the request tray, and nothing reaches them until you send it.'}
      </div>
      {mode?.top}
      {sections.map((section) => (
        <Section key={section.key} section={section} labels={labels} mode={mode} readOnly={readOnly} busy={busy} picked={picked} actions={actions} />
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
              <ColumnRow key={column.key} column={column} mode={mode} readOnly={readOnly} busy={busy} onAskColumn={actions.onAskColumn} />
            ))}
          </div>
        </div>
      )}
      {!sections.length && !page.columns && <div className="rr-rail-note">Nothing to ask on this tab.</div>}
      {mode?.foot}
    </div>
  );
}
