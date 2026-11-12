import { describe, expect, it } from 'vitest';
import { nextSlot, optionsFor, parseSlot, shownFields, slotKey, withoutSaved } from './formModel';

describe('questionnaire form model', () => {
  it('G43 reads and writes slot keys with stable row ids', () => {
    expect(parseSlot('plans.7.txtCurrPlanName')).toEqual({ block: 'plans', rowId: 7, field: 'txtCurrPlanName' });
    expect(parseSlot('txtCoName')).toEqual({ block: '', rowId: 0, field: 'txtCoName' });
    expect(slotKey('plans', 7, 'x')).toBe('plans.7.x');
    expect(slotKey('', 0, 'x')).toBe('x');
  });

  it('G41 Enter goes to the next question and Tab to the next blank required one, both wrapping', () => {
    const order = ['a', 'b', 'c', 'd'];
    expect(nextSlot(order, ['a', 'd'], 'b')).toBe('c');
    expect(nextSlot(order, ['a', 'd'], 'b', { required: true })).toBe('d');
    expect(nextSlot(order, ['a'], 'b', { required: true })).toBe('a');
    expect(nextSlot(order, [], 'b', { back: true })).toBe('a');
    expect(nextSlot(order, ['b'], 'b', { required: true })).toBe(null);
  });

  it('G40 a landed save keeps what was typed during it', () => {
    expect(withoutSaved({ a: '1', b: '22' }, { a: '1', b: '2' })).toEqual({ b: '22' });
  });

  it('G12 a dependent picker reads its row slice of the table by the server key', () => {
    const spec = { tables: { conditions_by_category: { 'Stomach/Esophagus': ['Hiatal Hernia'] } } };
    const field = { options_table: 'conditions_by_category' };
    expect(optionsFor(spec, field, 'conditions_by_category/Stomach/Esophagus')).toEqual(['Hiatal Hernia']);
    expect(optionsFor(spec, field, '')).toEqual([]);
    expect(optionsFor(spec, { options: ['Yes', 'No'] }, '')).toEqual(['Yes', 'No']);
  });

  it('G36 a row shows only the fields the server put on screen, never the auto row number', () => {
    const fields = [{ key: 'n', auto: 'row_number' }, { key: 'a' }, { key: 'b' }];
    expect(shownFields(fields, new Set(['plans.2.b', 'plans.2.n']), 'plans', 2).map((f) => f.key)).toEqual(['b']);
  });
});
