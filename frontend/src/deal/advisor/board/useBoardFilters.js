import { useMemo } from 'react';
import { useFindIndex } from '../../../api/quotes';
import { activeCount, filterQuotes, lineRules, lineSliders, quoteCarriers } from './filter';
import { carrierForms, otherHits, prepareIndex, runFinder } from './finder';

const OFF = { query: '', active: false, ids: new Set(), byLine: new Map() };

/*
 * The finder and the filters on one line's board (plan.md §8.14; F14–F27, F140): what the filter card shows and
 * which quotes the board draws. The finder searches every line's index (`plans/find/`) with the carriers' aliases
 * from /api/meta/; until the index has loaded it filters nothing. The line's sliders, caps and columns come from
 * meta (`board.sliders` by field set, `board.caps` and `board.columns` by line), never from a list here.
 */
export default function useBoardFilters({ dealId, meta, lines, line, config, quotes, sorted }) {
  const index = useFindIndex(dealId);
  const forms = useMemo(() => carrierForms(meta.carriers), [meta.carriers]);
  const prepared = useMemo(() => (index.data ? prepareIndex(index.data.plans) : null), [index.data]);
  const finder = useMemo(() => (prepared ? runFinder(prepared, config.find, forms) : OFF), [prepared, config.find, forms]);

  const board = meta.board;
  const lineKeys = useMemo(() => new Set(board.columns?.[line]?.all ?? []), [board, line]);
  const fieldSet = meta.lines.find((row) => row.key === line)?.field_set;
  const sliderDefs = (board.sliders?.[fieldSet] ?? []).filter((slider) => lineKeys.has(slider.key));
  const caps = board.caps?.[line] ?? [];
  const rules = lineRules(config, line, lineKeys);
  const sliders = lineSliders(sliderDefs, quotes, config);
  const result = filterQuotes(sorted, { config, finder, rules: rules.applied, sliders, caps });

  return {
    finder,
    others: otherHits(finder, line, lines.map((row) => ({ line: row.line, label: row.label }))),
    rules,
    sliders,
    caps,
    carriers: quoteCarriers(quotes),
    active: activeCount(config, { rules, sliders, caps }),
    ...result,
  };
}
