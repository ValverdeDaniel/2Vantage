import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import DropdownPop from './DropdownPop';
import GridCell from './GridCell';
import { HEAD_H, ROW_HEAD_W, WINDOW_FROM, columnLetter, prefix, rowWindow } from './gridModel';
import { cellKey } from './workbookModel';

/*
 * One tab of the client spreadsheet as Excel draws it (plan.md §8.14; J116; the old shared/WorkbookGrid.jsx at
 * 891f1b3): the server's worked-out tab in, a grid out. Two uses:
 * - the screen (`headers`): column letters and row numbers, the tab's frozen panes held while it scrolls, its zoom, a
 *   cell to select and the drop-downs' prompts and lists, read-only; rows drawn only as they scroll into view past
 *   WINDOW_FROM, since an All Plans tab can hold thousands;
 * - a printed page (`rows` / `cols` given): just the cells on that page with the rows and columns Excel repeats on it,
 *   no headers and no scrolling. `colScale` draws a printed page's columns wider while the type keeps its size.
 */
export default function WorkbookGrid({
  tab,
  model,
  zoom: zoomPct,
  colScale = 1,
  headers = true,
  rows: rowList = null,
  cols: colList = null,
  selected = null,
  onSelect = null,
  marks = null,
  scrollTo = null,
}) {
  const zoom = (zoomPct || tab.zoom || 100) / 100;
  const page = Boolean(rowList);
  const allRows = useMemo(() => Array.from({ length: tab.rows }, (_v, i) => i), [tab.rows]);
  const allCols = useMemo(() => Array.from({ length: tab.cols }, (_v, i) => i), [tab.cols]);
  const rowsShown = rowList || allRows;
  const colsShown = colList || allCols;
  const colWidth = (c) => Math.round((tab.col_px[c] || 64) * zoom * colScale);
  const colPx = colsShown.map(colWidth);
  const rowPx = rowsShown.map((r) => Math.max(1, Math.round((tab.row_px[r] || 20) * zoom)));
  const lefts = prefix(colPx);
  const tops = prefix(rowPx);
  const headH = headers ? HEAD_H : 0;
  const headW = headers ? ROW_HEAD_W : 0;
  const freeze = !page && tab.freeze ? tab.freeze : { rows: 0, cols: 0 };
  const scroller = useRef(null);
  const [view, setView] = useState({ top: 0, height: 800 });
  const [listAt, setListAt] = useState(null); // the cell whose list is open
  const colIndex = useMemo(() => new Map(colsShown.map((c, j) => [c, j])), [colsShown]);
  const windowed = !page && rowsShown.length > WINDOW_FROM;
  const { first, last } = rowWindow(tops, rowsShown.length, Math.min(freeze.rows, rowsShown.length), view, windowed);

  const onScroll = () => {
    const node = scroller.current;
    if (node && windowed) setView({ top: node.scrollTop, height: node.clientHeight });
  };
  useEffect(() => {
    const node = scroller.current;
    if (!node) return undefined;
    const observer = new ResizeObserver(() => setView({ top: node.scrollTop, height: node.clientHeight }));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  useLayoutEffect(() => {
    const node = scroller.current;
    if (node) node.scrollTop = 0; // another tab starts at its top, as Excel opens one
  }, [tab.title]);

  // Bring a cell into view below the frozen panes (a check clicked, an arrow key).
  useLayoutEffect(() => {
    const node = scroller.current;
    if (!node || !scrollTo || page) return;
    const i = rowsShown.indexOf(scrollTo.r);
    const j = colsShown.indexOf(scrollTo.c);
    if (i < 0 || j < 0) return;
    const frozenH = tops[freeze.rows];
    const frozenW = lefts[freeze.cols];
    if (i >= freeze.rows && (tops[i] - frozenH < node.scrollTop || tops[i + 1] + headH > node.scrollTop + node.clientHeight)) {
      node.scrollTop = Math.max(0, tops[i] - frozenH - 40);
    }
    if (j >= freeze.cols && (lefts[j] - frozenW < node.scrollLeft || lefts[j + 1] + headW > node.scrollLeft + node.clientWidth)) {
      node.scrollLeft = Math.max(0, lefts[j] - frozenW - 40);
    }
  }, [scrollTo]); // eslint-disable-line react-hooks/exhaustive-deps

  const selKey = selected ? cellKey(selected.r, selected.c) : null;
  const ctx = {
    tab,
    model,
    zoom,
    colsShown,
    colPx,
    colWidth,
    colIndex,
    rowPx,
    freeze,
    headers,
    headH,
    headW,
    tops,
    lefts,
    selected,
    marks,
    onSelect,
    onToggleList: () => setListAt((open) => (open === selKey ? null : selKey)),
  };

  let overlay = null;
  const drop = selected && onSelect ? model.drops.get(selKey) : null;
  if (drop) {
    const i = rowsShown.indexOf(selected.r);
    const j = colsShown.indexOf(selected.c);
    if (i >= 0 && j >= 0) {
      const span = model.heads.get(selKey);
      const right = lefts[j + (span ? span[1] : 1)] ?? lefts[lefts.length - 1];
      overlay = (
        <DropdownPop
          drop={drop}
          value={model.cells.get(selKey)?.[2]}
          open={listAt === selKey}
          x={headW + lefts[j]}
          y={headH + tops[i + 1]}
          minWidth={Math.max(180, right - lefts[j])}
        />
      );
    }
  }

  const images = (tab.images || []).map((img, n) => {
    const i = rowsShown.indexOf(img.r);
    const j = colsShown.indexOf(img.c);
    if (i < 0 || j < 0) return null;
    const box = { left: headW + lefts[j], top: headH + tops[i], width: img.w * zoom, height: img.h * zoom };
    return <img key={n} className="xg-img" src={img.src} alt="" style={box} />;
  });

  const drawRow = (i) => {
    const r = rowsShown[i];
    const top = i < freeze.rows ? headH + tops[i] : null;
    return (
      <tr key={r} style={{ height: rowPx[i] }}>
        {headers && (
          <th
            className={`xg-rowhead ${selected?.r === r ? 'xg-head-on' : ''}`}
            style={top !== null ? { top, zIndex: 6 } : undefined}
          >
            {/* Never taller than the row: a 3 pt rule row keeps its 3 pt. */}
            <div className="xg-rowhead-in" style={{ height: Math.max(1, rowPx[i] - 1) }}>
              {r + 1}
            </div>
          </th>
        )}
        {colsShown.map((c, j) => (
          <GridCell key={c} ctx={ctx} r={r} i={i} c={c} j={j} />
        ))}
      </tr>
    );
  };
  const body = [];
  for (let i = 0; i < Math.min(freeze.rows, rowsShown.length); i += 1) body.push(drawRow(i));
  if (first > freeze.rows) {
    body.push(<tr key="above" aria-hidden="true" style={{ height: tops[first] - tops[freeze.rows] }} />);
  }
  for (let i = first; i <= last; i += 1) body.push(drawRow(i));
  if (last < rowsShown.length - 1) {
    body.push(<tr key="below" aria-hidden="true" style={{ height: tops[rowsShown.length] - tops[last + 1] }} />);
  }

  const totalW = headW + lefts[lefts.length - 1];
  const table = (
    <div className="xg-sheet" style={{ width: totalW, height: headH + tops[tops.length - 1] }}>
      <table className={`xg-table ${tab.gridlines && !page ? 'xg-gridlines' : ''}`} style={{ width: totalW }}>
        <colgroup>
          {headers && <col style={{ width: ROW_HEAD_W }} />}
          {colPx.map((px, j) => (
            <col key={colsShown[j]} style={{ width: px }} />
          ))}
        </colgroup>
        {headers && (
          <thead>
            <tr style={{ height: HEAD_H }}>
              <th className="xg-corner" />
              {colsShown.map((c, j) => (
                <th
                  key={c}
                  className={`xg-colhead ${selected?.c === c ? 'xg-head-on' : ''}`}
                  style={j < freeze.cols ? { left: headW + lefts[j], zIndex: 7 } : undefined}
                >
                  {columnLetter(c)}
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>{body}</tbody>
      </table>
      {images}
      {overlay}
    </div>
  );

  if (page) return table;
  return (
    <div className="xg-scroll" ref={scroller} onScroll={onScroll}>
      {table}
    </div>
  );
}
