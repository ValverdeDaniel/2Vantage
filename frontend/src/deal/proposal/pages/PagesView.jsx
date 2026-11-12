import { useCallback, useMemo, useState } from 'react';
import { useMeta } from '../../../api/meta';
import { usePages } from '../../../api/proposals';
import { useFindIndex } from '../../../api/quotes';
import { carrierForms } from '../../../lib/findText';
import ConfirmDialog from '../../../ui/ConfirmDialog';
import InlineError from '../../../ui/InlineError';
import PageTable from './PageTable';
import PlanMenu from './PlanMenu';
import PlanPicker from './PlanPicker';
import { columnsById, shownPages } from './pageRows';
import { movedNote, pageMemo } from './pageToast';
import { searchPlaces } from './pickerRows';
import usePageWrites from './usePageWrites';

/*
 * "What the client will see" (plan.md §8.14; F37–F39, F45, F46, F48, J5–J13; the old ProposalPages.jsx at 7385bb3,
 * D-221): a line's comparison pages as the PowerPoint prints them, one table per page, plans as columns left to right.
 * The Advisor mounts it as ▦ Pages (its Columns tab picks the rows); the builder's Plans card mounts it with Key rows
 * or All rows, "Our recommendation" (`recommend`: {keepable: [current plan ids], disabled}) and ⋯ More (`withMenu`).
 *
 * The pages are the server's (`GET proposal/pages/`, the one splitter): six plans a page, a renewal page three pairs
 * a page, a page per current plan once quotes say what they replace. Nothing here works out a page, a figure or a rule.
 * Clicking an option's name opens the plan picker; the arrows reorder; ✕ takes a plan off; "Replacing:" links it;
 * "＋ Add a plan" puts one beside a current plan. With nothing starred it shows the first two pages; a write that adds
 * a page says which plan moved. On the builder, "See the slides ▸" (`onSlides`) opens the Export viewer's PowerPoint
 * (J58).
 */
export default function PagesView({
  dealId,
  line,
  lineLabel,
  preset,
  intro = null,
  recommend = null,
  withMenu = false,
  onSlides = null,
}) {
  const query = usePages(dealId, line, preset);
  const payload = query.data?.line === line ? query.data : null;
  const writes = usePageWrites(dealId, line, payload);
  const { data: meta } = useMeta();
  const index = useFindIndex(dealId);
  const [picker, setPicker] = useState(null); // {spot, anchor} | {spot: null, anchor} ("＋ Add a plan")
  const [showAll, setShowAll] = useState(false);
  const [confirm, setConfirm] = useState(null); // the plan ✕ would take off, when it is recommended
  const [seen, setSeen] = useState({ key: null, memo: null, moved: '' });

  const byId = useMemo(() => columnsById(payload), [payload]);
  const places = useMemo(() => searchPlaces(index.data, line), [index.data, line]);
  const forms = useMemo(() => carrierForms(meta?.carriers ?? []), [meta]);
  const close = useCallback(() => setPicker(null), []);

  // A refetch that adds a page names the plan that moved (F38): compared once per new set of pages.
  const pages = payload?.pages ?? [];
  const key = payload ? `${line}|${pages.map((page) => page.plan_ids.join('-')).join('|')}` : null;
  if (key && key !== seen.key) {
    const note = movedNote(seen.memo, line, pages, byId, lineLabel);
    setSeen({ key, memo: pageMemo(line, pages), moved: note || (seen.memo?.line === line ? seen.moved : '') });
  }

  if (query.isError && !payload) {
    return <InlineError title="What the client will see" error={query.error} onRetry={() => query.refetch()} />;
  }
  if (!payload) return <div className="bnf-pg-loading">Laying out the slides…</div>;

  const { pages: shown, folded, foldable } = shownPages(pages, payload.nothing_starred, showAll);
  const actions = {
    openPicker: (spot, anchor) => setPicker({ spot, anchor }),
    move: writes.move,
    link: writes.link,
    recommend: writes.recommend,
    remove: (plan) => (plan.remove.unrecommend ? setConfirm(plan) : writes.takeOff(plan)),
  };
  const choose = (plan, extra) => {
    const open = picker;
    close();
    if (open?.spot) writes.pick(plan, open.spot);
    else writes.add(plan, extra?.beside ?? null);
  };

  return (
    <div className="bnf-advisor-pages">
      {intro}
      {payload.off ? (
        <div className="bb-empty">
          {lineLabel} is off the proposal: {payload.off}.
        </div>
      ) : !pages.length ? (
        <div className="bb-empty">Nothing on the {lineLabel} proposal yet.</div>
      ) : (
        <div className="bnf-pg">
          {seen.moved && (
            <div className="bnf-pg-moved" role="status">
              {seen.moved}
              <button type="button" className="bnf-override-link" onClick={() => setSeen({ ...seen, moved: '' })}>
                OK
              </button>
            </div>
          )}
          {folded && (
            <div className="bnf-pg-folded">
              Nothing is starred, so all {payload.quotes} {lineLabel} quotes print on {pages.length} pages. Pick plans
              into the pages below, or star the ones to show.
            </div>
          )}
          {shown.map((page) => (
            <PageTable
              key={`${page.n}-${page.plan_ids.join('-')}`}
              page={page}
              count={pages.length}
              payload={payload}
              byId={byId}
              busy={writes.busy}
              openId={picker?.spot?.plan_id ?? null}
              actions={actions}
              recommend={recommend}
              menu={withMenu ? (plan) => <PlanMenu plan={plan} busy={writes.busy} onRename={writes.rename} /> : null}
            />
          ))}
          {foldable && (
            <button type="button" className="bnf-override-link bnf-pg-showall" onClick={() => setShowAll((on) => !on)}>
              {showAll ? 'Show the first two pages' : `Show every page (${pages.length})`}
            </button>
          )}
          {payload.quotes > 0 && (
            <div className="bnf-pg-addrow">
              <button
                type="button"
                className="bnf-pg-add"
                disabled={writes.busy}
                onClick={(event) => setPicker({ spot: null, anchor: event.currentTarget })}
              >
                ＋ Add a plan
              </button>
              {!payload.several && payload.landing[''] && <span className="bnf-pg-addnote">{payload.landing['']}</span>}
              {onSlides && (
                <button type="button" className="bnf-override-link bnf-pg-slides" onClick={onSlides}>
                  See the slides ▸
                </button>
              )}
            </div>
          )}
        </div>
      )}
      {picker && (
        <PlanPicker
          payload={payload}
          lineLabel={lineLabel}
          anchor={picker.anchor}
          spot={picker.spot}
          places={places}
          forms={forms}
          onChoose={choose}
          onClose={close}
        />
      )}
      <ConfirmDialog
        open={Boolean(confirm)}
        title={`Take ${confirm?.name ?? ''} off the proposal?`}
        message={`${confirm?.words ?? ''} is recommended. Taking it off the proposal also takes away the recommendation.`}
        confirmLabel="Take it off"
        tone="danger"
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          const plan = confirm;
          setConfirm(null);
          writes.takeOff(plan);
        }}
      />
    </div>
  );
}
