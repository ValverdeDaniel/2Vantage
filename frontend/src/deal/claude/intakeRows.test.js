import { describe, expect, it } from 'vitest';
import { contactText, coverageText, intakeRows, shownAnswer } from './intakeRows';

describe('an intake read in the review card (B40, D112)', () => {
  it('B40 shows answers as the form does', () => {
    expect(shownAnswer('2027-01-01')).toBe('01/01/2027');
    expect(shownAnswer(['FL', 'GA'])).toBe('FL, GA');
    expect(shownAnswer(null)).toBe('—');
    expect(shownAnswer('12-3456789')).toBe('12-3456789');
  });

  it('B40 says whether a coverage line is added or its blanks filled', () => {
    const values = [
      { key: 'carrier', label: 'Carrier', new: 'Example Health Plan', shown: 'Example Health Plan' },
      { key: 'funding', label: 'Funding', new: 'fully_insured', shown: 'Fully insured' },
    ];
    expect(coverageText({ label: 'Medical', coverage: null, values })).toBe(
      'Medical — add: Example Health Plan · Funding Fully insured',
    );
    expect(coverageText({ label: 'Medical', coverage: 4, values: values.slice(1) })).toBe(
      'Medical — fill the blanks: Funding Fully insured',
    );
  });

  it('B40 lists a contact by name, title, email and role', () => {
    const contact = { name: 'Jordan Example', title: 'HR Manager', email: 'j@example.com', role_label: 'HR Admin' };
    expect(contactText(contact)).toBe('Jordan Example, HR Manager · j@example.com · HR Admin');
  });

  it('B40 splits the items into their three parts', () => {
    const rows = intakeRows({
      items: [
        { id: 'answer:fein', op: 'answer', new: '12-3456789', old: null },
        { id: 'coverage:medical', op: 'coverage', label: 'Medical', coverage: null, values: [] },
        { id: 'contact:1', op: 'contact', name: 'Jordan Example' },
      ],
    });
    expect(rows.answers[0].was).toBe('—');
    expect(rows.coverage).toHaveLength(1);
    expect(rows.contacts[0].text).toBe('Jordan Example');
  });
});
