import { describe, expect, it } from 'vitest';
import { askWords, chipWords, columnChips, needYou, paneOf, sectionsOf, shown } from './requestModel';

const items = [
  { ref: 'intake:legal_name', section: 'Company', status: 'on_file' },
  { ref: 'intake:fein', section: 'Company', status: 'missing' },
  { ref: 'intake:dba', section: 'Company', status: 'in_cart' },
  { ref: 'intake:total_employees', section: 'Employees', status: 'asked', asked_at: '2026-10-20T14:00:00Z' },
];

describe('L29 the ask list by section', () => {
  it('keeps the items’ order and says what "＋ Add all" takes', () => {
    const sections = sectionsOf(items);
    expect(sections.map((section) => [section.key, section.items.length, section.toAsk])).toEqual([
      ['Company', 3, ['intake:fein']],
      ['Employees', 1, []],
    ]);
    expect(askWords(sections[0])).toBe('1 to ask');
    expect(askWords(sections[1])).toBe('none left to ask');
  });
  it('lifts what the deal needs and is missing into "Required to market" first', () => {
    const needed = items.map((item) => (item.ref === 'intake:fein' ? { ...item, needed: true } : item));
    const sections = sectionsOf(needed);
    expect(sections.map((section) => [section.key, section.items.map((item) => item.ref)])).toEqual([
      ['Required to market', ['intake:fein']],
      ['Company', ['intake:legal_name', 'intake:dba']],
      ['Employees', ['intake:total_employees']],
    ]);
  });
  it('words each chip, the asked date included', () => {
    const labels = { asked: 'Asked', in_cart: 'In the tray', on_file: 'On file' };
    expect(chipWords(items[3], labels)).toBe('Asked · Oct 20');
    expect(chipWords(items[1], labels)).toBe('');
    expect(chipWords(items[2], labels)).toBe('In the tray');
  });
});

describe('L27 L46 Show chips, census columns and the header', () => {
  it('a Show chip keeps its status', () => {
    expect(shown(items, 'missing').map((item) => item.ref)).toEqual(['intake:fein']);
    expect(shown(items, 'all')).toHaveLength(4);
  });
  it('a column says what is in the tray, asked, open and blank', () => {
    expect(columnChips({ in_cart: 2, asked: 0, on_link: true, blank: 3, questions: 1, answered: 0 })).toEqual([
      ['2 in the tray', 'rr-rail-chip-cart'],
      ['On their form', 'rr-rail-chip-asked'],
      ['1 question open', 'rr-rail-chip-question'],
      ['3 blank', ''],
    ]);
    expect(columnChips({ blank: 0 })).toEqual([['On file', 'rr-rail-chip-file']]);
  });
  it('picks the tab and counts what needs us', () => {
    expect(paneOf(new URLSearchParams('pane=census'))).toBe('census');
    expect(paneOf(new URLSearchParams('pane=payroll'))).toBe('intake');
    expect(needYou([{ waiting: 2 }, { waiting: 1 }, {}])).toBe(3);
  });
});
