import { useMemo } from 'react';
import { useFindIndex } from '../../../api/quotes';
import { setPick } from '../../shared/boardBridge';
import { activeCount, filterQuotes, lineRules, lineSliders, quoteCarriers } from './filter';
import { carrierForms, otherHits, prepareIndex, runFinder } from './finder';
import { usePick } from './useBoardBridge';

const OFF = { query: '', active: false, ids: new Set(), byLine: new Map() };

/*
 * The finder and the filters on one line's board (plan.md §8.14; F14–F27, F140): what the filter card shows and
 * which quotes the board draws. The finder searches every line's index (`plans/find/`) with the carriers' aliases
 * from /api/meta/; until the index has loaded it filters nothing. The line's sliders, caps and columns come from
 * meta (`board.sliders` by field set, `board.caps` and `board.columns` by line), never from a list here. Claude's
 * pick (F25; slice 24) keeps only the plans it judged a match, on the line it judged them on, and counts as active.
 */
export default function useBoardFilters({ dealId, meta, lines, line, config, quotes, sorted }) {
  const index = useFindIndex(dealId);
  const forms = useMemo(() => carrierForms(meta.carriers), [meta.carriers]);
  const prepared = useMemo(() => (index.data ? prepareIndex(index.data.plans) : null), [index.data]);
  const finder = useMemo(() => (prepared ? runFinder(prepared, config.find, forms) : OFF), [prepared, config.find, forms]);
  const pick = usePick(dealId);

  const board = meta.board;
  const lineKeys = useMemo(() => new Set(board.columns?.[line]?.all ?? []), [board, line]);
  const fieldSet = meta.lines.find((row) => row.key === line)?.field_set;
  const sliderDefs = (board.sliders?.[fieldSet] ?? []).filter((slider) => lineKeys.has(slider.key));
  const caps = board.caps?.[line] ?? [];
  const rules = lineRules(config, line, lineKeys);
  const sliders = lineSliders(sliderDefs, quotes, config);
  const result = filterQuotes(sorted, { config, finder, rules: rules.applied, sliders, caps });
  const pickOn = pick && pick.line === line ? pick : null;
  const picked = pickOn ? new Set(pickOn.plan_ids) : null;
  const judged = pickOn ? new Set(pickOn.judged_ids ?? pickOn.plan_ids) : null;

  return {
    finder,
    others: otherHits(finder, line, lines.map((row) => ({ line: row.line, label: row.label }))),
    rules,
    sliders,
    caps,
    carriers: quoteCarriers(quotes),
    active: activeCount(config, { rules, sliders, caps }) + (pick ? 1 : 0),
    ...result,
    shown: picked ? result.shown.filter((plan) => picked.has(plan.id)) : result.shown,
    pick: pick ? { ...pick, on: Boolean(pickOn), unjudged: judged ? quotes.filter((plan) => !judged.has(plan.id)).length : 0 } : null,
    clearPick: () => setPick(dealId, null),
  };
}
