import { describe, expect, it } from 'vitest';
import {
  activeCount,
  barTitle,
  censusColumns,
  EMPTY_CENSUS,
  EMPTY_INTAKE,
  intakeRows,
  intakeSections,
  neededGaps,
  originTotals,
  peopleWord,
} from './boardModel';

const rows = [
  { ref: 'intake:fein', key: 'fein', label: 'FEIN', section: 'employer', section_label: 'Employer', status: 'gap', needed: true, shown: true, origin: '' },
  { ref: 'intake:dba', key: 'dba', label: 'DBA', section: 'employer', section_label: 'Employer', status: 'answered', needed: false, shown: true, origin: 'typed' },
  { ref: 'intake:union', key: 'union', label: 'Union', section: 'eligibility', section_label: 'Eligibility', status: 'gap', needed: true, shown: true, origin: '', draft_id: 4 },
  { ref: 'intake:hidden', key: 'hidden', label: 'Hidden one', section: 'eligibility', section_label: 'Eligibility', status: 'optional', needed: false, shown: false, origin: '' },
];

const column = (key, extra = {}) => ({
  key,
  label: key.toUpperCase(),
  group: 'identity',
  rule: 'auto',
  required: false,
  quoted: true,
  applies: 'all',
  origins: {},
  counts: { missing: 0, na: 0, low: 0, client: 0, high: 2 },
  ...extra,
});

describe('the intake board (B37)', () => {
  it('B37 filters by section, status, origin and search, and hides hidden questions until searched', () => {
    expect(intakeRows(rows, EMPTY_INTAKE).map((row) => row.key)).toEqual(['fein', 'dba', 'union']);
    expect(intakeRows(rows, { ...EMPTY_INTAKE, statuses: ['gap'] }).map((row) => row.key)).toEqual(['fein', 'union']);
    expect(intakeRows(rows, { ...EMPTY_INTAKE, origins: ['typed'] }).map((row) => row.key)).toEqual(['dba']);
    expect(intakeRows(rows, { ...EMPTY_INTAKE, search: 'hidden' }).map((row) => row.key)).toEqual(['hidden']);
    expect(intakeRows(rows, { ...EMPTY_INTAKE, hideAnswered: true, section: 'employer' }).map((row) => row.key)).toEqual(['fein']);
  });

  it('B37 select needed gaps skips what is in the tray or asked', () => {
    expect(neededGaps(rows)).toEqual(['intake:fein']);
  });

  it('B37 names the sections and counts the origins', () => {
    expect(intakeSections(rows).map((s) => s.key)).toEqual(['employer', 'eligibility']);
    expect(originTotals(rows)).toEqual({ typed: 1 });
    expect(activeCount({ ...EMPTY_INTAKE, search: 'x', statuses: ['gap'] }, EMPTY_INTAKE)).toBe(2);
  });
});

describe('the census board (C27)', () => {
  const columns = [
    column('dob', { required: true, counts: { missing: 2, na: 0, low: 0, client: 1, high: 1 } }),
    column('zip', { rule: 'waived', counts: { missing: 0, na: 3, low: 0, client: 0, high: 1 }, origins: { import: 1 } }),
    column('hire_date', { group: 'employment', applies: 'employee', quoted: false }),
  ];

  it('C27 keeps columns by group, status, requiredness, completeness, quoting, waiver and origin', () => {
    const keys = (filters) => censusColumns(columns, { ...EMPTY_CENSUS, ...filters }).map((c) => c.key);
    expect(keys({ group: 'employment' })).toEqual(['hire_date']);
    expect(keys({ statuses: ['missing'] })).toEqual(['dob']);
    expect(keys({ statuses: ['client'] })).toEqual(['dob']);
    expect(keys({ requiredOnly: true })).toEqual(['dob']);
    expect(keys({ hideComplete: true })).toEqual(['dob', 'zip']);
    expect(keys({ quotedOnly: true })).toEqual(['dob', 'zip']);
    expect(keys({ hideWaived: true })).toEqual(['dob', 'hire_date']);
    expect(keys({ origins: ['import'] })).toEqual(['zip']);
  });

  it('C27 words the bar from the segments and counts employees for employee-only columns', () => {
    const segments = [
      { key: 'missing', label: 'Missing — required on this deal' },
      { key: 'client', label: 'Supplied by the client, pending approval' },
      { key: 'high', label: 'Filled' },
    ];
    expect(barTitle(columns[0], segments)).toBe('2 missing — required on this deal · 1 supplied by the client, pending approval · 1 filled');
    expect(peopleWord(columns[2])).toBe('employees');
    expect(peopleWord(columns[0])).toBe('people');
  });
});
