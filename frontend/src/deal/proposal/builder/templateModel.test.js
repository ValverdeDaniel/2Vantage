import { describe, expect, it } from 'vitest';
import { layoutConfig, matchesConfig, rowsChanges, rowsConfig, summaryConfig } from './templateModel';

const output = {
  layout: 'by_carrier',
  package_summary: true,
  compare_slots: 16,
  pages: { agenda: true, team: false },
  cover: { on: true, image: null },
  pictures: { cover: 'blue_light', agenda: null },
};

describe('J68 templates', () => {
  it('turns the resolved output into its setting paths', () => {
    expect(layoutConfig(output)).toEqual({
      'output.layout': 'by_carrier',
      'output.package_summary': true,
      'output.compare_slots': 16,
      'output.pages.agenda': true,
      'output.pages.team': false,
      'output.cover.on': true,
      'output.cover.image': null,
      'output.pictures.cover': 'blue_light',
      'output.pictures.agenda': null,
    });
  });

  it('reads a built-in as chosen only while the deal holds each of its paths', () => {
    const current = layoutConfig(output);
    expect(matchesConfig(current, { 'output.layout': 'by_carrier', 'output.cover.image': null })).toBe(true);
    expect(matchesConfig(current, { 'output.pages.team': true })).toBe(false);
  });

  it('applies a rows template on the line it is used on, and saves the summary as picked', () => {
    expect(rowsConfig({ rows: null, card_stats: ['coinsurance'] })).toEqual({ rows: null, card_stats: ['coinsurance'] });
    expect(rowsChanges('dental', { rows: ['den_ortho'] })).toEqual({
      'lines.dental.rows': ['den_ortho'],
      'lines.dental.card_stats': null,
    });
    expect(summaryConfig({ on: false, picked: [{ key: 'today' }] })).toEqual({
      'summary.on': false,
      'summary.blocks': [{ key: 'today' }],
    });
  });
});
