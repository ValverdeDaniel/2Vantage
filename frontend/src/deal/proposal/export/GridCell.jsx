import { cellKey } from './workbookModel';
import { FLAGS, VA, columnLetter, edge, lookStyle, spillRoom } from './gridModel';

/*
 * One cell of the workbook grid as Excel draws it (plan.md §8.14; J116; the old WorkbookGrid renderCell at 891f1b3):
 * its look at the tab's zoom, held in place over a frozen pane, ringed when selected or checked; a line of text runs on
 * over empty neighbours (right, left for right-aligned, both ways for centred) and is cut at the next full one; a number
 * never runs on; text is cut at the cell's edge, never "…". A merge a page break cut draws the part on its page from
 * the merge's own cell, its text laid across the whole merge. `ctx` is the grid's per-render geometry.
 */
export default function GridCell({ ctx, r, i, c, j }) {
  const { tab, model, zoom, colsShown, colPx, colWidth, colIndex, rowPx, freeze, headers } = ctx;
  const { cells, heads, covered, headOf, drops } = model;
  let k = cellKey(r, c);
  let shift = 0;
  let headC = c;
  if (covered.has(k)) {
    const [hr, hc] = headOf.get(k) || [r, c];
    const prev = j > 0 ? colsShown[j - 1] : null;
    const headHere = colIndex.has(hc) && hr === r;
    const runGoesOn = prev !== null && prev >= hc && prev < c && headOf.get(cellKey(r, prev))?.[1] === hc;
    if (hr !== r || headHere || runGoesOn) return null;
    headC = hc;
    k = cellKey(r, hc);
    for (let n = hc; n < c; n += 1) shift += colWidth(n);
  }
  const span = heads.get(k);
  let colSpan = 1;
  if (span) {
    const from = headC === c ? 1 : c - headC + 1; // the merge's columns on this page (a page may cut it)
    let n = from;
    while (n < span[1] && colIndex.get(headC + n) === j + (n - from + 1)) {
      colSpan += 1;
      n += 1;
    }
  }
  const cut = Boolean(span) && (shift > 0 || colSpan < span[1] - (headC === c ? 0 : c - headC));
  const fullW = span ? Array.from({ length: span[1] }, (_v, n) => colWidth(headC + n)).reduce((a, b) => a + b, 0) : 0;
  const st = tab.styles[tab.looks[r]?.[headC] || 0] || {};
  const item = cells.get(k);
  const text = item ? item[2] : '';
  const flags = item ? item[3] : 0;
  const extra = item?.[4] || {};
  const style = lookStyle(st, zoom);
  const top = i < freeze.rows ? ctx.headH + ctx.tops[i] : null;
  const left = j < freeze.cols ? ctx.headW + ctx.lefts[j] : null;
  if (top !== null || left !== null) {
    style.position = 'sticky';
    if (top !== null) style.top = top;
    if (left !== null) style.left = left;
    style.zIndex = top !== null && left !== null ? 4 : 3;
    if (!style.background) style.background = '#fff';
  }
  const isSel = ctx.selected?.r === r && ctx.selected?.c === c;
  const mark = ctx.marks?.get(k);
  const cls = [
    'xg-cell',
    isSel && 'xg-sel',
    mark && `xg-mark-${mark}`,
    flags & FLAGS.HASHED && 'xg-hashed',
    flags & FLAGS.LINK && 'xg-link',
    i === freeze.rows - 1 && 'xg-freeze-row',
    j === freeze.cols - 1 && 'xg-freeze-col',
  ]
    .filter(Boolean)
    .join(' ');
  const pad = extra.pad ? (
    <span className="xg-pad" aria-hidden="true">
      {extra.pad}
    </span>
  ) : null;
  // The row's height holds the text, never the other way round: as tall as the row (its merge's rows) less borders.
  let tall = 0;
  for (let n = 0; n < (span ? span[0] : 1) && i + n < rowPx.length; n += 1) tall += rowPx[i + n];
  const inner = {
    height: Math.max(1, tall - edge(st.bb) - edge(st.bt)),
    justifyContent: VA[st.va || 'bottom'] || 'flex-end',
    ...(st.ind ? { paddingLeft: 2 + st.ind * 9 * zoom } : {}),
    ...(cut ? { width: fullW - 4, marginLeft: -shift } : {}),
  };
  let body = (
    <div className="xg-in" style={inner}>
      <div className="xg-text">
        {text}
        {pad}
      </div>
    </div>
  );
  const textual = text && !(flags & (FLAGS.NUMBER | FLAGS.ERROR | FLAGS.LOGICAL)) && !st.wrap && !span;
  if (textual) {
    const holds = (col) => cells.has(cellKey(r, col)) || covered.has(cellKey(r, col)) || heads.has(cellKey(r, col));
    const align = st.ha || 'left';
    const right = align === 'left' || align === 'justify' ? spillRoom(colsShown, colPx, j, 1, holds) : 0;
    const leftRoom = align === 'right' ? spillRoom(colsShown, colPx, j, -1, holds) : 0;
    const both =
      align === 'center' ? Math.min(spillRoom(colsShown, colPx, j, 1, holds), spillRoom(colsShown, colPx, j, -1, holds)) : 0;
    if (right || leftRoom || both) {
      const spill = {
        justifyContent: align === 'right' ? 'flex-end' : align === 'center' ? 'center' : 'flex-start',
        alignItems: VA[st.va || 'bottom'] || 'flex-end',
        width: colPx[j] + right + leftRoom + both * 2,
        height: inner.height,
        ...(align === 'right' ? { right: 0 } : { left: -both }),
        paddingLeft: inner.paddingLeft,
      };
      body = (
        <span className="xg-spill" style={spill}>
          {text}
          {pad}
        </span>
      );
      style.overflow = 'visible';
      if (style.position !== 'sticky') style.position = 'relative';
      if (!style.zIndex) style.zIndex = 1;
    }
  }
  const drop = drops.get(k);
  const title = extra.real
    ? `${extra.real} (the column is too narrow, so Excel shows ####)`
    : flags & FLAGS.LINK
      ? 'In Excel this opens the plan’s SBC'
      : undefined;
  return (
    <td
      colSpan={colSpan > 1 ? colSpan : undefined}
      className={cls}
      style={style}
      title={title}
      onClick={ctx.onSelect ? () => ctx.onSelect(r, c) : undefined}
      data-cell={headers ? `${columnLetter(c)}${r + 1}` : undefined}
    >
      {body}
      {isSel && drop && ctx.onToggleList && (
        <button
          type="button"
          className="xg-dd"
          aria-label="Show the list"
          onClick={(event) => {
            event.stopPropagation();
            ctx.onToggleList();
          }}
        >
          ▾
        </button>
      )}
    </td>
  );
}
