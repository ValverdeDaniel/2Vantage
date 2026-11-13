import { describe, expect, it } from 'vitest';
import { dayBefore, linkStatus, othersWaiting, peopleOf, statusNote } from './settingsModel';

const requests = [
  {
    id: 3,
    asks: ['Intake gaps'],
    message: 'Hi',
    state: 'waiting',
    closed_at: null,
    recipients: [
      { link_id: 11, name: 'Dana', revoked: false, expired: false, can_restore: false, can_extend: true },
      { link_id: 12, name: 'Lee', revoked: true, expired: false, can_restore: true, can_extend: false },
    ],
  },
  { id: 4, asks: [], message: '', state: 'closed', closed_at: '2026-11-01', recipients: [{ link_id: 13, name: '', revoked: false, expired: true }] },
];

describe('People & links and the settings card (L38, L39)', () => {
  it('L38 lists every link with its request and how it stands', () => {
    const people = peopleOf(requests);
    expect(people.map((p) => [p.link_id, p.request_id, linkStatus(p)])).toEqual([
      [11, 3, 'active'],
      [12, 3, 'revoked'],
      [13, 4, 'closed'],
    ]);
    expect(people[0].asks).toEqual(['Intake gaps']);
  });

  it('L39 says what the switch does in each state', () => {
    const [dana, lee, nobody] = peopleOf(requests);
    expect(statusNote(dana, 'Dana')).toMatch(/^Off: the link stops opening now/);
    expect(statusNote(lee, 'Lee')).toMatch(/^On: the same link opens again/);
    expect(statusNote(nobody, 'Private link')).toBe('Its request was closed, so this link no longer opens.');
  });

  it('L39 names someone else’s change going with this update', () => {
    const people = peopleOf(requests);
    expect(othersWaiting({ 11: { blank: true }, 12: { expires_on: '2026-11-20', nudge_on: '2026-11-18' } }, 11, people)).toEqual([
      'Lee’s Expires and Remind me to nudge',
    ]);
  });

  it('I36 a reminder may be set at the latest the day before the link runs out', () => {
    expect(dayBefore('2026-11-20')).toBe('2026-11-19');
    expect(dayBefore('')).toBe('');
  });
});
