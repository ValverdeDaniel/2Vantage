import { useState } from 'react';
import { useDeal } from '../../../api/deals';
import { useProposal } from '../../../api/proposals';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import BuilderToolbar from './BuilderToolbar';
import CoverCard from './CoverCard';
import CoverageCard from './CoverageCard';
import EnrollmentStrip from './EnrollmentStrip';
import FirmPagesDrawer from './FirmPagesDrawer';
import IncumbentCard from './IncumbentCard';
import LineTabs from './LineTabs';
import MarketsCard from './MarketsCard';
import NextStepsCard from './NextStepsCard';
import OffNotice from './OffNotice';
import OutputCard from './OutputCard';
import PagesCard from './PagesCard';
import { LayoutTemplates, RowsTemplates, SummaryTemplates } from './PartTemplates';
import PicturesCard from './PicturesCard';
import PlansCard from './PlansCard';
import RowsCard from './RowsCard';
import SummaryCard from './SummaryCard';
import { chooseLine, lineOrder, readRowsPref, writeRowsPref } from './builderModel';
import useBuilderCards from './useBuilderCards';
import useBuilderWrites from './useBuilderWrites';

const storage = () => (typeof window === 'undefined' ? null : window.localStorage);

/*
 * The proposal builder, the Advisor's "Proposal builder" view (plan.md §8.14; J17–J20, J23, J27–J31, J38–J67; the old
 * ProposalBuilder.jsx at 891f1b3, split by responsibility), in the old card order: the toolbar (marks, checks, the
 * readiness banner); the deal cards Cover, Pictures, How the documents look, Presentation pages (with team picks and
 * plan experience) and Coverage & marketing intent; the line tabs, and per line the Plans card (or a kept line's
 * incumbent card) with the EnrollmentStrip and the rows card; then the Executive summary, Next steps and the line's
 * Markets checked. The layout, rows and summary cards carry their TEMPLATE bars (J68); the Firm pages drawer (J155)
 * opens from the Presentation pages card and a firm page's Fix ▸ (slice 34).
 *
 * "Open proposal ▸" calls `onExport`: the Advisor shows its Export viewer (J27; slice 28); "See the slides ▸" on the
 * Plans card calls `onSlides`: the viewer on the PowerPoint, at the line's first plan set (J58; slice 30).
 *
 * The payload is the server's (GET deals/{id}/proposal/): this holds only which card is open, which line is shown, Key
 * rows / All rows and whether the checks are open. An edit clears its card's mark on the server (J19); there is no save
 * queue (J20).
 */
export default function ProposalBuilder({
  dealId,
  meta,
  line: wantedLine,
  onLine,
  onQuotes,
  onGoTab,
  onExport,
  onSlides,
}) {
  const proposal = useProposal(dealId);
  const writes = useBuilderWrites(dealId);
  const client = useDeal(dealId).data?.client?.name ?? '';
  const [showChecks, setShowChecks] = useState(false);
  const [firmOpen, setFirmOpen] = useState(false);
  const [rowsMode, setRowsMode] = useState(() => readRowsPref(storage()));
  const [picked, setPicked] = useState(null); // a kept line with no plans is the builder's alone, so it keeps its own
  const data = proposal.data;
  const key = chooseLine(data?.lines ?? [], picked ?? wantedLine);
  const pickLine = (next) => {
    setPicked(next);
    onLine(next);
  };
  const proposalMeta = meta.proposal;
  const cards = useBuilderCards({ proposalMeta, stored: data?.marks.stored, line: key, writes, onLine: pickLine, onGoTab });

  if (proposal.isPending) return <Loading label="Loading the proposal…" />;
  if (proposal.isError && !data) {
    return <InlineError title="Proposal builder" error={proposal.error} onRetry={() => proposal.refetch()} />;
  }
  if (!data.lines.length) {
    return (
      <div className="bb-panel">
        <div className="bb-panel-title">Nothing to build yet</div>
        <div className="bb-panel-sub">
          Confirm the coverage intent and read some quotes first — the proposal is built from the lines you are
          marketing.
        </div>
      </div>
    );
  }

  const line = data.lines.find((entry) => entry.line === key);
  const set = writes.setPath;
  const lineLabel = (lineKey) => meta.lines?.find((entry) => entry.key === lineKey)?.label ?? lineKey;
  const marketChoices = data.config.markets?.lines?.[key] ?? {};
  const strip = (
    <EnrollmentStrip
      key={key}
      line={line}
      labels={meta.enrollment?.labels ?? {}}
      busy={writes.busy}
      onSave={(figures) => writes.saveEnrollment(key, figures)}
      onAdvisor={onQuotes}
    />
  );
  const actions = {
    resetOrder: () => writes.resetOrder(key),
    toQuotes: onQuotes,
    toSlides: onSlides,
    recommendAll: writes.recommendAll,
    reasons: (text) => set(`reasons.${key}`, text),
  };
  const pickRows = (mode) => {
    setRowsMode(mode);
    writeRowsPref(storage(), mode);
  };
  const fix = (item) => (item.fix?.drawer === 'firm' ? setFirmOpen(true) : cards.fix(item));
  const writing = { busy: writes.busy, onApply: writes.setPaths };

  return (
    <div className="bnf-build" data-guide="proposal-builder">
      <BuilderToolbar
        progress={cards.progress}
        allOpen={cards.allOpen}
        onAllOpen={cards.setAllOpen}
        checks={data.checks}
        showChecks={showChecks}
        onShowChecks={setShowChecks}
        ready={data.ready}
        onFix={cards.fix}
        onOpenProposal={onExport}
      />
      <CoverCard
        output={data.output}
        words={{ title: data.config.title ?? '', intro: data.config.intro ?? '' }}
        client={client}
        meta={proposalMeta}
        card={cards.props('cover')}
        busy={writes.busy}
        onSet={set}
      />
      <PicturesCard
        output={data.output}
        meta={proposalMeta}
        card={cards.props('pictures')}
        busy={writes.busy}
        onSet={set}
        onSetMany={writes.setPaths}
      />
      <OutputCard
        output={data.output}
        meta={proposalMeta}
        bestOnly={data.best_only}
        card={cards.props('output')}
        busy={writes.busy}
        onSet={set}
        templates={<LayoutTemplates output={data.output} {...writing} />}
      />
      <PagesCard
        ledger={data.ledger}
        output={data.output}
        experience={data.experience}
        team={data.config.team ?? null}
        meta={proposalMeta}
        card={cards.props('pages')}
        busy={writes.busy}
        onSet={set}
        onFix={fix}
        onFirm={() => setFirmOpen(true)}
      />
      <FirmPagesDrawer open={firmOpen} meta={proposalMeta} onClose={() => setFirmOpen(false)} />
      <CoverageCard dealId={dealId} meta={meta} card={cards.props('coverage')} />
      <LineTabs
        lines={data.lines}
        line={key}
        busy={writes.busy}
        onPick={pickLine}
        onMove={(lineKey, dir) => {
          const order = lineOrder(data.lines, lineKey, dir);
          if (order) set('order', order);
        }}
      />
      {line.state === 'presented' ? (
        <IncumbentCard
          line={line}
          card={cards.props('quotes')}
          strip={strip}
          onEditIntent={() => cards.fix({ fix: { card: 'coverage' } })}
        />
      ) : (
        <PlansCard
          dealId={dealId}
          line={line}
          card={cards.props('quotes')}
          rowsMode={rowsMode}
          onRowsMode={pickRows}
          notice={
            <OffNotice
              line={line}
              busy={writes.busy}
              onOpenIntent={() => cards.fix({ fix: { card: 'coverage' } })}
              onPutOn={(hasToday) => writes.putOn(key, hasToday)}
            />
          }
          strip={line.off ? null : strip}
          busy={writes.busy}
          actions={actions}
        />
      )}
      <RowsCard
        line={line}
        card={cards.props('rows')}
        meta={proposalMeta}
        busy={writes.busy}
        onSet={set}
        templates={<RowsTemplates key={key} line={line} {...writing} />}
      />
      <SummaryCard
        summary={data.summary}
        lines={data.lines}
        lineLabel={lineLabel}
        newGroup={!data.lines.some((entry) => entry.currents.length)}
        meta={proposalMeta}
        card={cards.props('summary')}
        busy={writes.busy}
        onSet={set}
        templates={<SummaryTemplates summary={data.summary} {...writing} />}
      />
      <NextStepsCard
        key={JSON.stringify(data.next_steps)}
        steps={data.next_steps}
        meta={proposalMeta}
        card={cards.props('next_steps')}
        busy={writes.busy}
        onSet={set}
      />
      <MarketsCard
        markets={data.markets}
        line={line}
        settings={{ notes: marketChoices.notes ?? {}, hidden: marketChoices.hidden ?? [] }}
        meta={proposalMeta}
        card={cards.props('markets')}
        busy={writes.busy}
        onSet={set}
      />
    </div>
  );
}
