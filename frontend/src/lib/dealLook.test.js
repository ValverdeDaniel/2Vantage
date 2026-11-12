import { describe, expect, it } from 'vitest';
import { initialsOf, stagePillClass, statusBadgeClass } from './dealLook';

describe('the stage pill (M15)', () => {
  it('M15 keeps the old classes for the old stages', () => {
    expect(stagePillClass('intake')).toBe('bb-stage-pill bb-stage-extracting');
    expect(stagePillClass('quoting')).toBe('bb-stage-pill bb-stage-review');
    expect(stagePillClass('sold')).toBe('bb-stage-pill bb-stage-complete');
    expect(stagePillClass('lost')).toBe('bb-stage-pill bb-stage-lost');
  });

  it('M15 gives proposal a pill of its own', () => {
    const others = ['intake', 'quoting', 'sold', 'lost'].map(stagePillClass);
    expect(others).not.toContain(stagePillClass('proposal'));
    expect(stagePillClass('proposal')).toMatch(/^bb-stage-pill bb-stage-/);
  });

  it('M15 draws an unknown stage as intake', () => {
    expect(stagePillClass('enrollment')).toBe(stagePillClass('intake'));
  });
});

describe('the client status badge (CL9)', () => {
  it('CL9 tells the three statuses apart', () => {
    const badges = ['prospect', 'new_client', 'existing_client'].map(statusBadgeClass);
    expect(new Set(badges).size).toBe(badges.length);
    badges.forEach((badge) => expect(badge).toMatch(/^bb-badge bb-badge-/));
  });
});

describe('the avatar initials (I76)', () => {
  it('I76 takes the first letters of the first two words', () => {
    expect(initialsOf('Golden Dental Group')).toBe('GD');
    expect(initialsOf('acme')).toBe('A');
    expect(initialsOf('  Two   Spaces ')).toBe('TS');
    expect(initialsOf('')).toBe('?');
  });
});
