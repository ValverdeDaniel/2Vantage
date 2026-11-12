import { describe, expect, it } from 'vitest';
import { readerLine, sourceDocument, viewerFind } from './sourceTarget';

describe('E18 viewerFind', () => {
  it('opens the page the read recorded, with the value and the column words', () => {
    const find = viewerFind({ doc: 7, page: 3, line: 'Employee only $512.34' }, '512.34', 'Aetna Gold');
    expect(find).toEqual({
      page: 3,
      cell: '',
      value: '512.34',
      snippet: 'Employee only $512.34',
      hint: 'Aetna Gold',
      exact: false,
    });
  });

  it('prefers the located page and printed figure, and marks a single hit exact', () => {
    const loc = { state: 'found', page: 4, hits: 1, printed: '80%' };
    expect(viewerFind({ page: 3, loc }, '20')).toMatchObject({ page: 4, value: '80%', exact: true });
    expect(viewerFind({ page: 3, loc: { state: 'absent', page: 9 } }, '20')).toMatchObject({ page: 3, value: '20' });
  });

  it('opens a sheet value on its cell, and a page in the link wins', () => {
    expect(viewerFind({ cell: 'Medical!C7' }, '1500').cell).toBe('Medical!C7');
    expect(viewerFind({ loc: { state: 'found', sheet: 'Rates', cell: 'B3' } }, '1').cell).toBe('Rates!B3');
    expect(viewerFind({ page: 3 }, '1', '', '5').page).toBe(5);
    expect(viewerFind(null, null)).toMatchObject({ page: null, cell: '', value: '' });
  });

  it('drops the printed note from the reader line', () => {
    expect(readerLine('Coinsurance 80% · printed "80%"')).toBe('Coinsurance 80%');
    expect(readerLine('printed "80%"')).toBe('');
  });

  it('opens the locator file before the source file', () => {
    expect(sourceDocument({ doc: 3, loc: { doc: 5 } })).toBe(5);
    expect(sourceDocument({ doc: 3 })).toBe(3);
    expect(sourceDocument(undefined)).toBe(null);
  });
});
