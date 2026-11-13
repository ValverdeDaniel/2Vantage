import { describe, expect, it } from 'vitest';
import { censusBoxes, intakeBoxes, nextBox, originWords, toSave } from './editModel';

describe('edit mode (L35)', () => {
  const items = [
    { ref: 'intake:fein', needed: true, status: 'missing' },
    { ref: 'intake:dba', needed: false, status: 'missing' },
    { ref: 'intake:block:contacts', needed: false, status: 'missing' },
    { ref: 'intake:sic_code', needed: true, status: 'on_file' },
    { ref: 'intake:website', needed: true, status: 'missing' },
  ];

  it('L35 lists the intake questions as boxes, never a block', () => {
    expect(intakeBoxes(items).map((box) => box.ref)).toEqual(['intake:fein', 'intake:dba', 'intake:sic_code', 'intake:website']);
  });

  it('L35 Enter goes to the next box, Tab to the next required blank', () => {
    const boxes = intakeBoxes(items);
    expect(nextBox(boxes, 'intake:fein')).toBe('intake:dba');
    expect(nextBox(boxes, 'intake:fein', true)).toBe('intake:website');
    expect(nextBox(boxes, 'intake:website')).toBe('');
  });

  it('L35 lists the census blanks person by person', () => {
    const blanks = { people: [{ cells: [{ ref: 'census:1:dob', required: true }] }, { cells: [{ ref: 'census:2:zip', required: false }] }] };
    expect(censusBoxes(blanks)).toEqual([
      { ref: 'census:1:dob', required: true, blank: true },
      { ref: 'census:2:zip', required: false, blank: true },
    ]);
  });

  it('L35 a box saves only something new', () => {
    expect(toSave('  32801 ', '')).toBe('32801');
    expect(toSave('', 'x')).toBeNull();
    expect(toSave('same', 'same')).toBeNull();
    expect(originWords(true)).toMatch(/client/);
  });
});
