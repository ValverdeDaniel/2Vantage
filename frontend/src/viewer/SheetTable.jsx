/*
 * One window of a spreadsheet as a table (plan.md §8.16; E27, E29, D-167; OQ25): Plain, or "As in Excel" from the
 * `format` that documents/sheet_look.py sends beside the rows (fills, fonts, borders, merges, widths, heights). The
 * text in every cell is still `rows`, what a reader saw: no number is reformatted. What Excel hides is shown, greyed
 * and tagged, since a read skips it. The opened cell is ringed (`bnf-sheet-hit`) and its row and column heads marked.
 */

const ROW_HEAD_PX = 44;
const PT_PX = 4 / 3;
export const HIDDEN_NOTE = 'Hidden in Excel. A quote read and Work with Claude skip hidden sheets, rows and columns.';
const NUMERIC = /^\(?-?[$€£]?\s*-?[\d,]*\.?\d+\s*%?\)?$/; // Excel's "General" puts a number on the right
// Fonts whose letters are pictures, drawn as Excel draws them; the cell's text is unchanged.
const SYMBOLS = {
  wingdings: { ü: '✓', û: '✗', ý: '☒', þ: '☑', o: '□', q: '❑', n: '■', l: '●', '§': '▪', Ø: '➢' },
  wingdings2: { P: '✓', O: '✗', R: '☑', T: '☒', Q: '☒', '£': '☐' },
};

function symbolText(text, sym) {
  const map = SYMBOLS[sym];
  return map ? [...text].map((ch) => map[ch] ?? ch).join('') : text;
}

/** One cell's look as an inline style (sheet_style.cell_style's keys). */
function cellStyle(st, text) {
  const s = {};
  if (st.bg) s.background = st.bg;
  if (st.fg) s.color = st.fg;
  if (st.b) s.fontWeight = 700;
  if (st.i) s.fontStyle = 'italic';
  if (st.u || st.x) s.textDecoration = [st.u && 'underline', st.x && 'line-through'].filter(Boolean).join(' ');
  if (st.s) s.fontSize = `${Math.round(st.s * PT_PX * 10) / 10}px`;
  if (st.ff) s.fontFamily = `"${st.ff}", Calibri, Arial, sans-serif`;
  s.textAlign = st.ha || (NUMERIC.test(text.trim()) ? 'right' : 'left');
  if (st.va) s.verticalAlign = st.va;
  if (st.wrap) s.whiteSpace = 'pre-wrap';
  if (st.ind) s.paddingLeft = `${3 + st.ind * 9}px`;
  if (st.bt) s.borderTop = st.bt;
  if (st.br) s.borderRight = st.br;
  if (st.bb) s.borderBottom = st.bb;
  if (st.bl) s.borderLeft = st.bl;
  return s;
}

const axis = (hit, hidden) =>
  [hit && 'bnf-sheet-hitaxis', hidden && 'bnf-sheet-hiddenaxis'].filter(Boolean).join(' ') || undefined;

function PlainTable({ data, hit, hitRef }) {
  return (
    <table className="bnf-sheet-table">
      <thead>
        <tr>
          <th className="bnf-sheet-corner" aria-hidden="true" />
          {data.col_letters.map((letter, c) => (
            <th key={letter} className={axis(hit && hit.col === c)}>
              {letter}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.rows.map((row, i) => {
          const r = data.start + i;
          const hitRow = hit && hit.row === r;
          return (
            <tr key={r}>
              <th className={axis(hitRow)}>{r + 1}</th>
              {row.map((cell, c) => {
                const isHit = hitRow && hit.col === c;
                return (
                  <td
                    key={c}
                    ref={isHit ? hitRef : null}
                    className={isHit ? 'bnf-sheet-hit' : undefined}
                    title={cell.length > 40 ? cell : undefined}
                  >
                    {cell}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function ExcelTable({ data, fmt, hit, hitRef }) {
  const spans = new Map();
  const covered = new Set();
  for (const [r, c, rs, cs] of fmt.merges) {
    spans.set(`${r}|${c}`, [rs, cs]);
    for (let i = r; i < r + rs; i += 1) {
      for (let j = c; j < c + cs; j += 1) if (i !== r || j !== c) covered.add(`${i}|${j}`);
    }
  }
  const hiddenCols = new Set(fmt.hidden_cols);
  const hiddenRows = new Set(fmt.hidden_rows);
  const width = ROW_HEAD_PX + fmt.col_px.reduce((sum, px) => sum + px, 0);
  // Excel lets a line of text run on over empty cells to its right.
  const spills = (row, i, c) => c + 1 < row.length && !row[c + 1] && !covered.has(`${i}|${c + 1}`);
  return (
    <table className="bnf-sheet-table bnf-sheet-excel" style={{ width }}>
      <colgroup>
        <col style={{ width: ROW_HEAD_PX }} />
        {fmt.col_px.map((px, c) => (
          <col key={c} style={{ width: px }} />
        ))}
      </colgroup>
      <thead>
        <tr>
          <th className="bnf-sheet-corner" aria-hidden="true" />
          {data.col_letters.map((letter, c) => (
            <th
              key={letter}
              className={axis(hit && hit.col === c, hiddenCols.has(c))}
              title={hiddenCols.has(c) ? HIDDEN_NOTE : undefined}
            >
              {letter}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.rows.map((row, i) => {
          const r = data.start + i;
          const hitRow = hit && hit.row === r;
          const rowHidden = hiddenRows.has(i);
          const px = fmt.row_px[i];
          return (
            <tr key={r} style={px ? { height: px } : undefined}>
              <th className={axis(hitRow, rowHidden)} title={rowHidden ? HIDDEN_NOTE : undefined}>
                {r + 1}
              </th>
              {row.map((cell, c) => {
                if (covered.has(`${i}|${c}`)) return null;
                const span = spans.get(`${i}|${c}`);
                const st = fmt.styles[fmt.cells[i]?.[c] || 0] || {};
                const isHit = hitRow && hit.col === c;
                const shown = st.sym ? symbolText(cell, st.sym) : cell;
                const cls = [
                  isHit && 'bnf-sheet-hit',
                  cell && !st.wrap && !span && spills(row, i, c) && 'bnf-sheet-spill',
                  (rowHidden || hiddenCols.has(c)) && 'bnf-sheet-hiddencell',
                ]
                  .filter(Boolean)
                  .join(' ');
                return (
                  <td
                    key={c}
                    ref={isHit ? hitRef : null}
                    rowSpan={span ? span[0] : undefined}
                    colSpan={span ? span[1] : undefined}
                    className={cls || undefined}
                    style={cellStyle(st, cell)}
                    title={shown !== cell || cell.length > 40 ? cell : undefined}
                  >
                    {shown}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default function SheetTable({ data, fmt, hitRef }) {
  const hit = data.match && data.match.sheet === data.sheet ? data.match : null;
  if (!data.rows.length) return <div className="bnf-sheet-empty">This sheet is empty.</div>;
  return fmt ? (
    <ExcelTable data={data} fmt={fmt} hit={hit} hitRef={hitRef} />
  ) : (
    <PlainTable data={data} hit={hit} hitRef={hitRef} />
  );
}
