import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { fetchSheet, findInSheet } from '../api/documents';
import { errorText } from '../lib/errors';
import SheetTable, { HIDDEN_NOTE } from './SheetTable';

/*
 * An uploaded spreadsheet (plan.md §8.16; E27–E29, D-119, D-167; OQ25): sheet tabs (hidden ones tagged), 200-row
 * windows ("Rows a–b of n"), "▦ As in Excel" or Plain (remembered in this browser), and the cell a value came from,
 * ringed: `find.cell` ("Medical!C7") opens it directly; otherwise the value is found on the server, posted in the body
 * (never the URL, E28), with the reader's line first and the plan's carrier and name as the column hint.
 */

const LOOK_KEY = 'vantage.sheet.look';
const NO_LOOK = 'This file has no Excel formatting to show here (a CSV, an old .xls, or a very large workbook)';
const EXCEL_LOOK =
  "The carrier's colours, borders, merged cells and column widths. Every value is exactly what the reader saw.";
const readLook = () => {
  try {
    return window.localStorage.getItem(LOOK_KEY) === 'plain' ? 'plain' : 'excel';
  } catch {
    return 'excel';
  }
};

/** The window to open for a value: its cell, or the cell the server finds; `state` says which. */
async function openFor(documentId, find, look) {
  const lookParam = look === 'excel' ? { look: 1 } : {};
  let cell = find.cell || '';
  let state = cell ? 'found' : 'idle';
  if (!cell && (find.value || find.snippet)) {
    const body = { value: find.value || '', line: find.snippet || '', hint: find.hint || '' };
    const where = await findInSheet(documentId, body);
    cell = where.cell ? `${where.sheet}!${where.cell}` : '';
    state = where.state === 'found' ? 'found' : 'missing';
  }
  const data = await fetchSheet(documentId, cell ? { cell, ...lookParam } : lookParam);
  const found = state === 'found' && data.match;
  return { data, state: state === 'found' && !found ? 'missing' : state, cell: found ? cell : '', match: data.match };
}

export default function SheetViewer({ documentId, find = {}, jumpKey = 0 }) {
  // What is on screen, tagged with the find it answers ({key, data, state, cell, match} or {key, error}).
  const [shown, setShown] = useState({ key: '', data: null });
  const [loading, setLoading] = useState(false);
  const [look, setLook] = useState(readLook);
  const seq = useRef(0);
  const hitRef = useRef(null);
  const findKey = [documentId, find.cell, find.value, find.snippet, find.hint, jumpKey].join('|');

  /** Show what `promise` answers for `key`, unless a later request was made. */
  function settle(promise, key, mine) {
    promise
      .then((next) => mine === seq.current && setShown({ ...next, key }))
      .catch((err) => mine === seq.current && setShown({ key, data: null, error: errorText(err) }))
      .finally(() => mine === seq.current && setLoading(false));
  }

  // A new file or a new value: the server picks the sheet and the window around the cell.
  useEffect(() => {
    settle(openFor(documentId, find, look), findKey, ++seq.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [findKey]);

  useLayoutEffect(() => {
    hitRef.current?.scrollIntoView({ block: 'center', inline: 'center' });
  }, [shown]);

  if (shown.key === findKey && shown.error) {
    return (
      <div className="bb-pdf-notfound" data-render="error" role="alert">
        {shown.error}
      </div>
    );
  }
  const { data } = shown;
  if (!data || shown.key !== findKey) {
    return (
      <div className="bb-pdf-viewer" data-render="loading" data-find="searching">
        <div className="bnf-sheet-loading">
          <span className="bnf-spin" aria-hidden="true" /> Opening the spreadsheet…
        </div>
      </div>
    );
  }

  // Moving between sheets and windows keeps the opened cell ringed: its reference goes with every request.
  const opened = shown.cell ? { cell: shown.cell } : {};
  const go = (params, how = look) => {
    setLoading(true);
    const asked = fetchSheet(documentId, { ...params, ...opened, ...(how === 'excel' ? { look: 1 } : {}) });
    settle(
      asked.then((next) => ({ ...shown, data: next })),
      findKey,
      ++seq.current,
    );
  };
  const lastStart = Math.max(0, data.total_rows - data.window);
  const pickLook = (next) => {
    if (next === look) return;
    setLook(next);
    try {
      window.localStorage.setItem(LOOK_KEY, next);
    } catch {
      /* private mode */
    }
    go({ sheet: data.sheet, start: data.start }, next);
  };
  const fmt = look === 'excel' ? data.format : null;
  const sheetHidden = Boolean(fmt) && data.sheets.some((s) => s.name === data.sheet && s.hidden);
  const asked = Boolean(find.cell || find.value || find.snippet);
  const match = shown.match;

  return (
    <div className="bb-pdf-viewer bnf-sheet-viewer" data-render="ready" data-find={loading ? 'searching' : shown.state}>
      <div className="bb-pdf-toolbar bnf-sheet-toolbar">
        <span className="bnf-sheet-tabs" role="tablist" aria-label="Sheets">
          {data.sheets.map((s) => (
            <button
              key={s.name}
              type="button"
              role="tab"
              aria-selected={s.name === data.sheet}
              className={`bb-pdf-btn${s.name === data.sheet ? ' bnf-sheet-tab-on' : ''}${
                fmt && s.hidden ? ' bnf-sheet-tab-hidden' : ''
              }`}
              title={fmt && s.hidden ? HIDDEN_NOTE : undefined}
              onClick={() => s.name !== data.sheet && go({ sheet: s.name, start: 0 })}
            >
              {s.name}
              {fmt && s.hidden && <span className="bnf-sheet-hidtag">hidden</span>}
            </button>
          ))}
        </span>
        {loading && <span className="bnf-spin" aria-hidden="true" />}
        <span className="bnf-sheet-where">
          {asked &&
            (shown.state === 'found' && match ? (
              <span className="bb-pdf-foundnote">
                Found in ‘{match.sheet}’ {match.cell}
              </span>
            ) : (
              <span className="bb-pdf-notfound-inline">Not found in this workbook</span>
            ))}
        </span>
        <span className="bnf-sheet-look" role="group" aria-label="How the sheet looks">
          <button
            type="button"
            aria-pressed={look === 'excel'}
            className={`bb-pdf-btn${look === 'excel' ? ' bnf-sheet-tab-on' : ''}`}
            onClick={() => pickLook('excel')}
            title={look === 'excel' && !data.format ? NO_LOOK : EXCEL_LOOK}
          >
            ▦ As in Excel
          </button>
          <button
            type="button"
            aria-pressed={look === 'plain'}
            className={`bb-pdf-btn${look === 'plain' ? ' bnf-sheet-tab-on' : ''}`}
            onClick={() => pickLook('plain')}
            title="The values in a plain grid"
          >
            Plain
          </button>
        </span>
        <span className="bb-pdf-pageinfo">
          Rows {data.total_rows ? data.start + 1 : 0}–{Math.min(data.start + data.window, data.total_rows)} of{' '}
          {data.total_rows}
        </span>
        <button
          type="button"
          className="bb-pdf-btn"
          disabled={data.start <= 0}
          title="The rows before these"
          onClick={() => go({ sheet: data.sheet, start: Math.max(0, data.start - data.window) })}
        >
          ◂ Prev
        </button>
        <button
          type="button"
          className="bb-pdf-btn"
          disabled={data.start >= lastStart}
          title="The rows after these"
          onClick={() => go({ sheet: data.sheet, start: Math.min(lastStart, data.start + data.window) })}
        >
          Next ▸
        </button>
      </div>
      {sheetHidden && (
        <div className="bnf-sheet-hiddennote" role="note">
          This sheet is hidden in Excel. A quote read and Work with Claude skip it.
        </div>
      )}
      <div className="bnf-sheet-scroll">
        <SheetTable data={data} fmt={fmt} hitRef={hitRef} />
      </div>
    </div>
  );
}
