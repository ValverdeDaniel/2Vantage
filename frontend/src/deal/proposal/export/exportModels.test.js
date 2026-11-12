import { describe, expect, it } from 'vitest';
import { builtWords, chooseFile, FILES, previewError } from './exportFiles';
import { columnLetter, lookStyle, prefix, rowWindow, spillRoom, tabModel } from './gridModel';
import { pageCells, paperGeometry, printNotes } from './printedPage';
import {
  cellKey,
  checkList,
  countWords,
  markMap,
  readMode,
  requestedTab,
  stepCell,
  tabLevel,
  writeMode,
} from './workbookModel';

describe('J105 F136 the file chips', () => {
  it('picks the wanted file only when it has a view, else the spreadsheet', () => {
    expect(chooseFile('excel')).toBe('excel');
    expect(chooseFile('web')).toBe('excel');
    expect(chooseFile(undefined)).toBe('excel');
    const live = FILES.map((file) => ({ ...file, live: true }));
    expect(chooseFile('pdf', live)).toBe('pdf');
  });

  it('reads the build time and count', () => {
    expect(builtWords(null, 3, 'tab')).toBe('');
    expect(builtWords('2026-11-12T14:05:00', 1, 'tab')).toMatch(/^Built .+ · 1 tab$/);
    expect(builtWords('2026-11-12T14:05:00', 13, 'tab')).toMatch(/· 13 tabs$/);
  });

  it('J107 tells a refusal (the download’s words) from a failure', () => {
    const refusal = { response: { status: 409, data: { detail: 'No plans on this proposal yet.' } } };
    expect(previewError(refusal)).toEqual({ refused: 'No plans on this proposal yet.', failed: '' });
    expect(previewError({ response: { status: 500 } }).failed).toBeTruthy();
    expect(previewError(null)).toEqual({ refused: '', failed: '' });
  });
});

describe('J118 checks', () => {
  const tab = {
    rows: 10,
    cols: 6,
    merges: [[2, 1, 1, 3]],
    checks: {
      cut: [{ cell: 'B3', r: 2, c: 1 }],
      tight: [{ cell: 'B3', r: 2, c: 1 }, { cell: 'E5', r: 4, c: 4 }],
    },
  };

  it('dots a tab by its worst check and counts each kind', () => {
    expect(tabLevel({ cut: 1 })).toBe('bad');
    expect(tabLevel({ tight: 2 })).toBe('warn');
    expect(tabLevel({ error: 0, hash: 0, cut: 0, tight: 0 })).toBeNull();
    expect(countWords({ hash: 1, cut: 2, tight: 0 })).toEqual(['1 number shows ####', '2 cut off']);
  });

  it('lists checks worst first and marks each cell with the worse of its checks', () => {
    expect(checkList(tab).map((check) => check.kind)).toEqual(['cut', 'tight', 'tight']);
    const marks = markMap(checkList(tab));
    expect(marks.get(cellKey(2, 1))).toBe('bad');
    expect(marks.get(cellKey(4, 4))).toBe('warn');
  });

  it('moves the selection as Excel does over a merge', () => {
    expect(stepCell(tab, { r: 2, c: 0 }, 'ArrowRight')).toEqual({ r: 2, c: 1 });
    expect(stepCell(tab, { r: 2, c: 1 }, 'ArrowRight')).toEqual({ r: 2, c: 4 });
    expect(stepCell(tab, { r: 1, c: 2 }, 'ArrowDown')).toEqual({ r: 2, c: 1 });
    expect(stepCell(tab, { r: 0, c: 0 }, 'ArrowUp')).toEqual({ r: 0, c: 0 });
    expect(stepCell(tab, { r: 0, c: 0 }, 'Enter')).toBeNull();
  });

  it('asks for the opening tab under one key', () => {
    expect(requestedTab(null, 'Dynamic Medical Compare')).toBe('');
    expect(requestedTab('Dynamic Medical Compare', 'Dynamic Medical Compare')).toBe('');
    expect(requestedTab('Dental', 'Dynamic Medical Compare')).toBe('Dental');
  });

  it('keeps Screen or Printed pages per browser', () => {
    const store = new Map();
    const storage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, v) };
    expect(readMode(storage)).toBe('screen');
    writeMode(storage, 'pages');
    expect(readMode(storage)).toBe('pages');
  });
});

describe('J116 the grid', () => {
  it('names columns as Excel does', () => {
    expect([0, 25, 26, 51, 701].map(columnLetter)).toEqual(['A', 'Z', 'AA', 'AZ', 'ZZ']);
  });

  it('draws a look at the tab’s zoom', () => {
    const style = lookStyle({ b: true, s: 9, ha: 'right', bb: '1px solid #000000', bg: '#002060' }, 1.1);
    expect(style).toMatchObject({ fontWeight: 700, textAlign: 'right', background: '#002060' });
    expect(style.fontSize).toBe('13.2px');
    expect(lookStyle({}, 1).textAlign).toBe('left');
  });

  it('knows merge heads, the cells they cover and the drop-downs', () => {
    const model = tabModel({
      cells: [[0, 0, 'Plan', 0]],
      merges: [[1, 1, 2, 2]],
      dropdowns: [{ cells: [[5, 2, 5, 3]], list: ['A', 'B'] }],
    });
    expect(model.cells.get(cellKey(0, 0))[2]).toBe('Plan');
    expect(model.heads.get(cellKey(1, 1))).toEqual([2, 2]);
    expect(model.covered.has(cellKey(2, 2))).toBe(true);
    expect(model.covered.has(cellKey(1, 1))).toBe(false);
    expect(model.headOf.get(cellKey(2, 1))).toEqual([1, 1]);
    expect(model.drops.get(cellKey(5, 3)).list).toEqual(['A', 'B']);
  });

  it('draws only the rows near the view on a long tab, frozen rows always', () => {
    const tops = prefix(Array(500).fill(20));
    expect(rowWindow(tops, 500, 2, { top: 0, height: 400 }, false)).toEqual({ first: 2, last: 499 });
    const { first, last } = rowWindow(tops, 500, 2, { top: 2000, height: 400 }, true);
    expect(first).toBeGreaterThan(2);
    expect(last).toBeLessThan(499);
    expect(first * 20).toBeLessThanOrEqual(2040);
    expect(last * 20).toBeGreaterThanOrEqual(2400);
  });

  it('runs text on over empty neighbours up to a full one', () => {
    const holds = (c) => c === 3;
    expect(spillRoom([0, 1, 2, 3, 4], [64, 50, 40, 30, 20], 0, 1, holds)).toBe(90);
    expect(spillRoom([0, 1, 2, 3, 4], [64, 50, 40, 30, 20], 4, -1, holds)).toBe(0);
  });
});

describe('J117 printed pages', () => {
  const info = {
    scale: 64,
    paper: { w: 11, h: 8.5 },
    margins: { left: 0.25, right: 0.25, top: 0.75, bottom: 0.75, footer: 0.3 },
    centered: true,
    title_rows: [3, 5],
    title_cols: [0, 1],
    print_width: 1.1,
    fit: false,
    near_edge: true,
  };

  it('repeats the title rows and columns on later pages only', () => {
    expect(pageCells(info, { rows: [0, 9], cols: [0, 7] }, 50).rows[0]).toBe(0);
    const later = pageCells(info, { rows: [10, 20], cols: [8, 12] }, 50);
    expect(later.rows.slice(0, 3)).toEqual([3, 4, 5]);
    expect(later.cols.slice(0, 2)).toEqual([0, 1]);
    expect(pageCells(info, { rows: [40, 60], cols: [0, 1] }, 50).missing).toBe(true);
  });

  it('sets the tab on letter at its scale, centred across', () => {
    const geometry = paperGeometry(info, [100, 100], [0, 1], 1100);
    expect(geometry.paperW).toBe(1100);
    expect(geometry.paperH).toBeCloseTo(850);
    expect(geometry.k).toBeCloseTo(0.64 * (100 / 96));
    expect(geometry.left).toBeGreaterThan(0.25 * 100);
  });

  it('says when a tab only just fits', () => {
    expect(printNotes(info)).toHaveLength(1);
    expect(printNotes({ ...info, near_edge: false, fit: true, excel_picks: false })[0]).toMatch(/^Fit To/);
  });
});
