import { describe, expect, it } from 'vitest';
import { answersReducer, initialAnswers, liveRail, pendingAnswers, todoStatus } from './portalModel';
import { formDraft, formSeeds, formStatus, holdWords, liveFormItem, specOnScreen } from './questionnaireModel';

const STATE = {
  values: { txtRsnBid: 'Renewal Increase' },
  bases: { txtRsnBid: 'b1', chkMedCon: 'b2' },
  order: ['txtRsnBid', 'chkMedCon'],
  blocks: [],
  rows: {},
  progress: { filled: 1, total: 2, pct: 50 },
};
const CARD = { form: 'fl', narrowed: false, signed: null, state: STATE };

describe('questionnaires on the portal (slice 58)', () => {
  it('G88 seeds every slot on screen as a q: ref with its base', () => {
    const { values, bases } = formSeeds([CARD]);
    expect(values).toEqual({ 'q:fl:txtRsnBid': 'Renewal Increase', 'q:fl:chkMedCon': '' });
    expect(bases['q:fl:chkMedCon']).toBe('b2');
  });

  it('G25 adopts the slots a save reveals without touching what is being typed', () => {
    const page = { questionnaires: [CARD] };
    let state = initialAnswers(page);
    state = answersReducer(state, { type: 'set', ref: 'q:fl:chkMedCon', value: 'Yes' });
    const fresh = { ...STATE, order: [...STATE.order, 'txtMcComments'], bases: { ...STATE.bases, txtMcComments: 'b3' } };
    state = answersReducer(state, { type: 'adopt', ...formSeeds([{ form: 'fl', state: fresh }]) });
    expect(state.values['q:fl:chkMedCon']).toBe('Yes');
    expect(state.bases['q:fl:txtMcComments']).toBe('b3');
    expect(pendingAnswers(state)).toEqual({ 'q:fl:chkMedCon': { value: 'Yes', base: 'b2' } });
    expect(formDraft('fl', state)).toEqual({ chkMedCon: 'Yes' });
  });

  it('G95 a form is done only once signed, and says "please sign" when every answer is in', () => {
    const item = { key: 'questionnaire_fl', kind: 'questionnaire', label: 'Florida Blue' };
    const full = { ...STATE, progress: { filled: 2, total: 2, pct: 100 } };
    expect(liveFormItem(item, CARD, full).done).toBe(false);
    expect(formStatus(liveFormItem(item, CARD, full))).toBe('2 of 2 — please sign');
    const signed = liveFormItem(item, { ...CARD, signed: { name: 'Robin' } }, full);
    expect(signed.done).toBe(true);
    expect(todoStatus(signed)).toBe('signed');
    expect(liveFormItem(item, { ...CARD, narrowed: true }, full).done).toBe(true);
  });

  it('L81 the live rail counts a form from its latest state', () => {
    const page = { questionnaires: [CARD], checklist: { items: [{ key: 'questionnaire_fl', kind: 'questionnaire' }] } };
    const rail = liveRail(page, {}, {}, { fl: { ...STATE, progress: { filled: 2, total: 2, pct: 100 } } });
    expect(rail.items[0]).toMatchObject({ filled: 2, total: 2, done: false });
  });

  it('G22 shows only the sections holding something on screen', () => {
    const spec = {
      sections: [
        { key: 'a', fields: [{ key: 'txtRsnBid' }], blocks: [] },
        { key: 'b', fields: [{ key: 'other' }], blocks: ['plans'] },
      ],
    };
    expect(specOnScreen(spec, STATE).sections.map((s) => s.key)).toEqual(['a']);
  });

  it('G93 words the blanks that held a signature', () => {
    expect(holdWords({ filled: 7, total: 9 })).toBe('Not signed yet — 2 required answers are still blank.');
    expect(holdWords({ filled: 8, total: 9 })).toBe('Not signed yet — 1 required answer is still blank.');
  });
});
