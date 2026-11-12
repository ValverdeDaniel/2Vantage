import { describe, expect, it } from 'vitest';
import { formFileKind, formKinds, readsInto } from './drawerWords';
import { applyBody, initialPicks, readSections, rowText, rowWhere, signedNote, togglePick } from './formReads';
import { undoAsk, UNDO_ASK } from './readWords';

const READ = {
  id: 4,
  form: 'fl_blue_51',
  label: 'Florida Blue 51+',
  signed: false,
  entries: [
    { ref: 'numTAP', kind: 'answer', label: '8. Employees', new: '61', old: '58', state: 'replace', tick: true },
    { ref: 'dteAnnivDate', kind: 'answer', label: '2. Anniversary', new: '2027-01-01', old: '', state: 'fill', tick: false },
    { ref: 'drpNumCarr', kind: 'answer', label: '11. Switches', new: '2', old: '1', state: 'conflict', tick: false },
    {
      ref: 'row:conditions:1',
      kind: 'row',
      label: 'Row',
      block_label: 'Group Medical Conditions',
      number: 1,
      target_number: null,
      state: 'fill',
      tick: true,
      values: [{ key: 'drpMedCat', label: 'Medical Category', new: 'Kidney', old: '' }],
    },
    {
      ref: 'row:plans:1',
      kind: 'row',
      label: 'Row',
      block_label: 'Current plan',
      number: 1,
      target_number: 1,
      state: 'fill',
      tick: true,
      values: [{ key: 'numCurrRatePrem', label: 'Current Premium', new: '41250', old: '' }],
    },
  ],
};

describe("a filled form's read in the drawer (G99, G100, G102)", () => {
  it('G99 ticks what Claude proposes, and "Use this scan" sends nothing until a tick changes', () => {
    const initial = initialPicks([READ]);
    expect([...initial].sort()).toEqual(['fl_blue_51:numTAP', 'fl_blue_51:row:conditions:1', 'fl_blue_51:row:plans:1']);
    expect(applyBody(initial, initial)).toEqual({});
    const more = togglePick(initial, 'fl_blue_51:dteAnnivDate');
    expect(applyBody(more, initial).select).toContain('fl_blue_51:dteAnnivDate');
    expect(togglePick(more, 'fl_blue_51:dteAnnivDate').size).toBe(initial.size);
  });

  it('G99 lists answers, rows and what is left alone, dates as the form shows them', () => {
    const { answers, rows, conflicts } = readSections(READ);
    expect(answers.map((entry) => entry.ref)).toEqual(['numTAP', 'dteAnnivDate']);
    expect(answers[1].shown).toBe('01/01/2027');
    expect(conflicts.map((entry) => entry.ref)).toEqual(['drpNumCarr']);
    expect(rows.map((entry) => entry.where)).toEqual([
      'Group Medical Conditions 1 → a new row',
      'Current plan 1 → row 1 of the form',
    ]);
    expect(rowWhere(READ.entries[4])).toContain('row 1 of the form');
    const asked = { values: [{ label: 'How many people?', new: '2', old: '1' }, { label: 'Eligible:', new: '9', old: '' }] };
    expect(rowText(asked)).toBe('How many people? 2 (was 1) · Eligible: 9');
  });

  it('G99 says a signed form takes nothing', () => {
    expect(signedNote([READ])).toBe('');
    expect(signedNote([{ ...READ, signed: true }])).toMatch(/^Florida Blue 51\+ is signed, so nothing/);
  });

  it('G102 names the reading picker by the deal’s forms, armed first', () => {
    const meta = {
      questionnaires: {
        forms: [
          { key: 'fl_blue_51', file_kind: 'questionnaire' },
          { key: 'wp_lg', file_kind: 'questionnaire' },
          { key: 'stop_loss_siia', file_kind: 'stop_loss' },
        ],
      },
      ai: { targets: [{ key: 'questionnaire', kinds: ['questionnaire', 'stop_loss'], waits: true }] },
    };
    const forms = [
      { key: 'wp_lg', label: 'Warner Pacific 51+' },
      { key: 'fl_blue_51', label: 'Florida Blue 51+' },
    ];
    expect(formKinds(meta, forms, ['questionnaire', 'stop_loss'])).toEqual({
      kinds: ['questionnaire'],
      labels: { questionnaire: 'Warner Pacific 51+' },
    });
    expect(formKinds(meta, [], ['questionnaire', 'stop_loss']).kinds).toEqual(['questionnaire', 'stop_loss']);
    expect(formFileKind(meta, 'stop_loss_siia')).toBe('stop_loss');
    expect(readsInto(meta, 'stop_loss')).toMatchObject({ target: 'questionnaire', into: 'the questionnaire', members: true });
  });

  it('D73 asks before undoing a filled form’s read in its own words', () => {
    expect(undoAsk({ target: 'questionnaire' })).toMatch(/answers this read put on the form/);
    expect(undoAsk({ target: 'quotes' })).toBe(UNDO_ASK);
  });
});
