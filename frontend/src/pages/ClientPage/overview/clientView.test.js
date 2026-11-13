import { describe, expect, it } from 'vitest';
import { agendaTile, dayWords, effectiveTile, historyChips } from './clientView';

const row = (chips, extra = {}) => ({ deal_id: 9, year: 2027, current: true, chips, ...extra });

describe('the client Overview words (CL16, CL18, G116)', () => {
  it('says how far the effective date is, before and after', () => {
    expect(dayWords(50)).toBe('in 50d');
    expect(dayWords(0)).toBe('in 0d');
    expect(dayWords(-3)).toBe('3d ago');
    expect(effectiveTile({ date: '2027-01-01', days: 50 })).toEqual({ value: '50d', tone: '' });
    expect(effectiveTile({ date: '2026-01-01', days: -3 })).toEqual({ value: '3d ago', tone: 'bb-rose' });
    expect(effectiveTile(null)).toEqual({ value: '—', tone: 'bb-empty' });
  });

  it('reads the Agenda tile as overdue, else soon, else clear', () => {
    expect(agendaTile({ overdue: 2, soon: 1, total: 5 })).toEqual({ value: '2 overdue', tone: 'bb-rose', total: 5 });
    expect(agendaTile({ overdue: 0, soon: 1, total: 5 })).toEqual({ value: '1 soon', tone: 'bb-amber', total: 5 });
    expect(agendaTile({ overdue: 0, soon: 0, total: 0 })).toEqual({ value: 'clear', tone: 'bb-green', total: 0 });
  });

  it('chips a deal with its intake, census, forms and files, each opening its tab', () => {
    const chips = historyChips(
      row({
        intake: { answered: 9, needed: 12 },
        census: { employees: 60, dependents: 0 },
        forms: [
          { key: 'fl_blue_51', label: 'Florida Blue 51+', chip: 'Questionnaire', signed: true, started: true },
          { key: 'siia', label: 'SIIA', chip: 'Stop-loss', signed: false, started: false },
        ],
        documents: 1,
      }),
    );
    expect(chips.map((chip) => [chip.label, chip.tab])).toEqual([
      ['Intake', 'intake'],
      ['Census', 'census'],
      ['Questionnaire ✓', 'questionnaire?form=fl_blue_51'],
      ['Stop-loss', 'questionnaire?form=siia'],
      ['Docs', 'documents'],
    ]);
    expect(chips[1]).toMatchObject({ count: '60 EE', title: '60 employees on file — open the 2027 census' });
    expect(chips[2].title).toBe('Florida Blue 51+ — signed. Open the 2027 form.');
    expect(chips[3].title).toBe('SIIA — not started. Open the 2027 form.');
    expect(chips[4].title).toBe('1 file — open the 2027 documents');
  });

  it('shows no chip with nothing behind it', () => {
    expect(historyChips(row({ intake: null, census: null, forms: [], documents: 0 }))).toEqual([]);
  });
});
