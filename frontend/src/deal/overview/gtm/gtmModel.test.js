import { describe, expect, it } from 'vitest';
import {
  askRefOf,
  askTitleOf,
  formLink,
  formReviewLink,
  isOpen,
  marketButton,
  quoteRows,
  suffixOf,
  tabLink,
  toggled,
} from './gtmModel';

const doc = (over = {}) => ({ key: 'renewal', satisfy: 'document', status: 'missing', kind: 'renewal', ...over });

describe('Card 1 (M42–M61)', () => {
  it('M44 keeps a group open until it is met, then the toggle wins', () => {
    expect(isOpen({ key: 'census', met: false }, {})).toBe(true);
    expect(isOpen({ key: 'census', met: true }, {})).toBe(false);
    const after = toggled({}, { key: 'census', met: true });
    expect(after).toEqual({ census: true });
    expect(isOpen({ key: 'census', met: true }, after)).toBe(true);
    expect(toggled(after, { key: 'census', met: true })).toEqual({ census: false });
  });

  it('M54 asks for a missing document by its kind, a chosen fillable form to fill online, never a done one', () => {
    expect(askRefOf(doc())).toBe('doc:renewal');
    expect(askRefOf(doc({ status: 'done' }))).toBeNull();
    expect(askRefOf(doc({ key: 'medical_questionnaire', kind: 'questionnaire' }))).toBe('doc:questionnaire');
    const chosen = doc({ key: 'medical_questionnaire', kind: 'questionnaire', form_key: 'fl_blue_51' });
    expect(askRefOf(chosen)).toBe('qform:fl_blue_51');
    expect(askRefOf({ ...chosen, status: 'done', signed: true })).toBeNull();
    const disclosure = doc({ key: 'stop_loss_disclosure', kind: 'stop_loss', form_key: 'stop_loss_siia' });
    expect(askRefOf(disclosure)).toBe('qform:stop_loss_siia');
    expect(askRefOf(doc({ key: 'stop_loss_disclosure', kind: 'stop_loss' }))).toBe('doc:stop_loss');
    expect(askRefOf({ key: 'cobra', satisfy: 'attest', status: 'missing', kind: '' })).toBeNull();
    expect(askTitleOf('qform:fl_blue_51')).toBe('Add the form to the request tray: they fill it out online on their link');
    expect(askTitleOf('doc:renewal')).toBeUndefined();
  });

  it('M50 sends the client’s questionnaire answers to the review queue’s Questionnaire section', () => {
    expect(formReviewLink(7)).toBe('/deals/7/review?view=queue&section=questionnaire');
  });

  it('M50 M57 says a file is on hand, and a signed form is signed', () => {
    expect(suffixOf(doc({ has_document: true }))).toBe(' — on file');
    expect(suffixOf(doc({ has_document: true }), { form: true })).toBe(' — document on file');
    expect(suffixOf(doc({ has_document: true, signed: true }), { form: true })).toBe(' — signed');
    expect(suffixOf(doc())).toBe('');
  });

  it('M108 M109 opens the questionnaire, or the disclosure by its form', () => {
    expect(formLink(7, { key: 'questionnaire', item: { form_key: 'fl_blue_51' } })).toEqual({
      label: 'Open questionnaire ▸',
      to: '/deals/7/questionnaire',
    });
    expect(formLink(7, { key: 'stop_loss', item: { form_key: 'stop_loss_siia' } })).toEqual({
      label: 'Open disclosure ▸',
      to: '/deals/7/questionnaire?form=stop_loss_siia',
    });
    expect(formLink(7, { key: 'questionnaire', item: { form_key: '' } })).toBeNull();
  });

  it('M61 sends a ready deal to market from Intake, else opens Intake', () => {
    expect(marketButton(7, { badge: 'ready' })).toEqual({ label: 'Send to market ▸', to: '/deals/7/intake?focus=marketed' });
    expect(marketButton(7, { badge: 'blocked' })).toEqual({ label: 'Open intake ▸', to: '/deals/7/intake' });
    expect(tabLink(7, 'review', { section: 'census', lane: 'missing', blank: '' })).toBe(
      '/deals/7/review?section=census&lane=missing',
    );
  });
});

describe('Card 2 (M62)', () => {
  const rows = [
    { key: 'quotes_in', detail: '6 plans · 2 to review · 1 missing', at: null },
    { key: 'issued', detail: 'Proposal issued', at: '2026-11-02T15:00:00Z' },
  ];

  it('M62 takes the journey steps and their states, with the server’s details', () => {
    const journey = {
      journey: {
        modules: [
          { key: 'get_to_market', steps: [{ key: 'intake_ready', label: 'Intake ready', state: 'done' }] },
          {
            key: 'quote_to_close',
            steps: [
              { key: 'quotes_in', label: 'Quotes in', state: 'done' },
              { key: 'issued', label: 'Proposal issued', state: 'current' },
            ],
          },
        ],
      },
    };
    expect(quoteRows(journey, rows)).toEqual([
      { key: 'quotes_in', label: 'Quotes in', state: 'done', detail: '6 plans · 2 to review · 1 missing', at: null },
      { key: 'issued', label: 'Proposal issued', state: 'current', detail: 'Proposal issued', at: '2026-11-02T15:00:00Z' },
    ]);
  });

  it('M62 shows the server’s rows as to do until the journey arrives', () => {
    expect(quoteRows(undefined, rows).map((row) => [row.key, row.state])).toEqual([
      ['quotes_in', 'todo'],
      ['issued', 'todo'],
    ]);
  });
});
