import { describe, expect, it } from 'vitest';
import {
  acceptsText,
  cellClass,
  cellStatus,
  cellText,
  cellTitle,
  chipGroups,
  defaultHidden,
  depLabel,
  filledRefs,
  shownFields,
  shownValue,
  splitCell,
  withAnswer,
  withValue,
} from './rosterModel';

const census = {
  groups: [
    { key: 'identity', label: 'Identity' },
    { key: 'medical', label: 'Medical' },
    { key: 'dental', label: 'Dental' },
  ],
  group_lines: { medical: ['medical'], dental: ['dental'] },
  fields: [
    { key: 'first_name', label: 'First Name', group: 'identity', type: 'text', choices: [] },
    { key: 'dob', label: 'Date of Birth', group: 'identity', type: 'date', choices: [] },
    { key: 'medical_tier', label: 'Medical Tier', group: 'medical', type: 'tier', choices: [{ value: 'EE' }, { value: 'ES' }] },
    { key: 'dental_tier', label: 'Dental Tier', group: 'dental', type: 'tier', choices: [] },
  ],
};

const person = (extra = {}) => ({
  id: 7,
  kind: 'employee',
  values: { first_name: 'Avery', dob: '1980-01-15' },
  sources: { first_name: { origin: 'import' } },
  issues: {},
  missing: [],
  review: {},
  ...extra,
});

describe('C2 line chips', () => {
  it('toggles only the groups of lines, and starts with those out of scope hidden', () => {
    expect(chipGroups(census).map((group) => group.key)).toEqual(['medical', 'dental']);
    const hidden = defaultHidden(census, ['first_name', 'dob', 'medical_tier']);
    expect([...hidden]).toEqual(['dental']);
    expect(shownFields(census, hidden).map((field) => field.key)).toEqual(['first_name', 'dob', 'medical_tier']);
  });
});

describe('C3 a cell says what it is', () => {
  it('shows a required blank, a relayed value and a mark, mark first', () => {
    expect(cellStatus(person({ missing: ['medical_tier'] }), 'medical_tier')).toBe('missing');
    expect(cellStatus(person(), 'medical_tier')).toBe('na');
    expect(cellStatus(person({ sources: { first_name: { origin: 'relay' } } }), 'first_name')).toBe('client');
    expect(cellClass(person(), 'first_name')).toBe('bb-cell-high');
    expect(cellClass(person({ review: { first_name: 'check' } }), 'first_name')).toBe('bb-cell-check');
    const wrong = person({ issues: { dob: [{ severity: 'warning', message: 'Employee is 9 years old' }] } });
    expect(cellClass(wrong, 'dob')).toBe('bb-cell-high bnf-cell-warn');
    expect(cellTitle(wrong, census.fields[1])).toBe('Employee is 9 years old');
  });

  it('says what a coded column accepts', () => {
    expect(acceptsText(census.fields[2])).toBe('Accepts: EE · ES');
    expect(acceptsText({ choices: Array.from({ length: 51 }, (_, i) => ({ value: String(i) })) })).toBe(
      'Start typing to pick from the list.',
    );
    expect(cellTitle(person(), census.fields[2])).toBe('Accepts: EE · ES');
  });

  it('shows dates month-first, a required blank as ＋ Add and any other blank as —', () => {
    expect(shownValue(census.fields[1], '1980-01-15')).toBe('01/15/1980');
    expect(shownValue(census.fields[1], 'soon')).toBe('soon');
    const blank = person({ missing: ['medical_tier'] });
    expect(cellText(blank, census.fields[2])).toBe('＋ Add');
    expect(cellText(blank, census.fields[3])).toBe('—');
  });

  it('labels a dependent by relationship', () => {
    expect(depLabel(person({ values: { relationship: 'Domestic Partner' } }))).toBe('Partner');
    expect(depLabel(person({ values: {} }))).toBe('dep');
  });
});

describe('C6 the cached page follows a write', () => {
  const page = { summary: { errors: 1 }, review: { open: 0 }, members: [person(), person({ id: 8 })] };

  it('shows a typed value at once, then lays the answer over it', () => {
    const typed = withValue(page, 8, 'dob', '03/04/1979');
    expect(typed.members[1].values.dob).toBe('03/04/1979');
    expect(typed.members[0]).toBe(page.members[0]);
    const answered = withAnswer(typed, { member: person({ id: 8, values: { dob: '1979-03-04' } }), summary: { errors: 0 } });
    expect(answered.members[1].values).toEqual({ dob: '1979-03-04' });
    expect(answered.summary).toEqual({ errors: 0 });
    expect(splitCell('8|dob')).toEqual([8, 'dob']);
  });

  it('marks only picked cells that hold a value', () => {
    expect(filledRefs(page, new Set(['census:7:first_name', 'census:7:ssn', 'census:9:dob']))).toEqual([
      'census:7:first_name',
    ]);
  });
});
