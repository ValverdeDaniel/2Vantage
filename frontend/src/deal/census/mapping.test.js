import { describe, expect, it } from 'vitest';
import {
  badge,
  chooseField,
  dryRunWords,
  fieldOptions,
  fileWords,
  lastApplied,
  mappedCount,
  mappingChanges,
  removesSomeone,
  rowNumbers,
  waitingImport,
} from './mapping';

const entry = (column, field, extra = {}) => ({
  column,
  header: `H${column}`,
  field,
  confidence: 0.95,
  low: false,
  ...extra,
});

describe('C15 chooseField', () => {
  it('takes a census column from the column that had it', () => {
    const mapping = [entry(0, 'first_name'), entry(1, '')];
    const next = chooseField(mapping, 1, 'first_name');
    expect(next.map((e) => e.field)).toEqual(['', 'first_name']);
    expect(next[1]).toMatchObject({ confidence: 1, low: false });
  });

  it('ignores a column', () => {
    expect(chooseField([entry(0, 'dob', { low: true, confidence: 0.6 })], 0, '')[0]).toMatchObject({
      field: '',
      confidence: 0,
      low: false,
    });
  });
});

describe('C15 badge', () => {
  it('says Mapped, Check (n%) or Unmapped', () => {
    expect(badge(entry(0, 'dob')).label).toBe('Mapped');
    expect(badge(entry(0, 'dob', { low: true, confidence: 0.6 }))).toEqual({
      label: 'Check (60%)',
      className: 'bb-badge-amber',
    });
    expect(badge(entry(0, '')).className).toBe('bb-badge-gray');
  });
});

describe('C15 mappingChanges', () => {
  it('sends only the columns whose field moved', () => {
    const saved = [entry(0, 'first_name'), entry(1, ''), entry(2, 'dob')];
    const edited = chooseField(chooseField(saved, 1, 'last_name'), 2, '');
    expect(mappingChanges(saved, edited)).toEqual([
      { column: 1, field: 'last_name' },
      { column: 2, field: '' },
    ]);
    expect(mappingChanges(saved, saved)).toEqual([]);
    expect(mappedCount(edited)).toBe(2);
  });
});

describe('C15 vocabularies and rows', () => {
  it('reads the census columns from meta', () => {
    const meta = {
      census: { fields: [{ key: 'ext_emp_id', label: 'Emp ID' }] },
    };
    expect(fieldOptions(meta)).toEqual([{ value: 'ext_emp_id', label: 'Emp ID' }]);
    expect(fieldOptions(undefined)).toEqual([]);
    expect(rowNumbers(3)).toEqual([1, 2, 3]);
  });

  it('finds the waiting import and the last applied one', () => {
    const imports = [
      { id: 3, status: 'proposed', document_id: 9 },
      { id: 2, status: 'applied', document_id: 8 },
      { id: 1, status: 'applied', document_id: 7 },
    ];
    expect(waitingImport(imports).id).toBe(3);
    expect(lastApplied(imports).id).toBe(2);
    expect(waitingImport([])).toBeNull();
  });
});

describe('C17 dry run words', () => {
  const counts = {
    people: 3,
    employees: 2,
    dependents: 1,
    added: 1,
    changed: 1,
    unchanged: 1,
    removed: 2,
    kept: 0,
  };

  it('lists who is added, changed, removed and kept', () => {
    expect(dryRunWords(counts)).toBe('1 added · 1 changed · 2 removed · 0 kept · 1 unchanged');
    expect(fileWords(counts)).toBe('This file lists 3 people: 2 employees and 1 dependent.');
  });

  it('asks before anyone is removed', () => {
    expect(removesSomeone({ counts })).toBe(true);
    expect(removesSomeone({ counts: { ...counts, removed: 0 } })).toBe(false);
  });
});
