import { useState } from 'react';
import { useProposal } from '../../../api/proposals';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import BuilderToolbar from './BuilderToolbar';
import EnrollmentStrip from './EnrollmentStrip';
import IncumbentCard from './IncumbentCard';
import LineTabs from './LineTabs';
import OffNotice from './OffNotice';
import PlansCard from './PlansCard';
import RowsCard from './RowsCard';
import {
  cardId,
  chooseLine,
  isOpen,
  lineOrder,
  readRowsPref,
  shownCards,
  stampOf,
  writeRowsPref,
} from './builderModel';
import useBuilderWrites from './useBuilderWrites';

const storage = () => (typeof window === 'undefined' ? null : window.localStorage);

/*
 * The proposal builder, the Advisor's "Proposal builder" view (plan.md §8.14; J17–J20, J23, J27–J31, J47–J62; the old
 * ProposalBuilder.jsx at 891f1b3, split by responsibility). Which plans each line presents and which we recommend, what
 * its section shows, and whether the proposal is ready: the toolbar (marks, checks, the readiness banner), the line
 * tabs, and per line the Plans card (or a kept line's incumbent card) with the EnrollmentStrip, and the rows card. The
 * deal cards (cover, output, pages, coverage, summary, next steps, markets) join with slices 26 and 34.
 *
 * Every card collapses and can be marked completed; a completed card starts collapsed. The payload is the server's
 * (GET deals/{id}/proposal/): this holds only which card is open, which line is shown, Key rows / All rows and whether
 * the checks are open. An edit clears its card's mark on the server (J19); there is no save queue (J20).
 */
export default function ProposalBuilder({ dealId, meta, line: wantedLine, onLine, onQuotes, onGoTab }) {
  const proposal = useProposal(dealId);
  const writes = useBuilderWrites(dealId);
  const [openCards, setOpenCards] = useState({});
  const [showChecks, setShowChecks] = useState(false);
  const [rowsMode, setRowsMode] = useState(() => readRowsPref(storage()));
  const [picked, setPicked] = useState(null); // a kept line with no plans is the builder's alone, so it keeps its own

  if (proposal.isPending) return <Loading label="Loading the proposal…" />;
  if (proposal.isError && !proposal.data) {
    return <InlineError title="Proposal builder" error={proposal.error} onRetry={() => proposal.refetch()} />;
  }
  const data = proposal.data;
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

  const key = chooseLine(data.lines, picked ?? wantedLine);
  const pickLine = (next) => {
    setPicked(next);
    onLine(next);
  };
  const line = data.lines.find((entry) => entry.line === key);
  const stored = data.marks.stored;
  const proposalMeta = meta.proposal;
  const cards = shownCards(proposalMeta, key);
  const setOpen = (card, open) => setOpenCards((now) => ({ ...now, [cardId(card)]: open }));
  const cardProps = (cardKey) => {
    const perLine = proposalMeta.cards.find((entry) => entry.key === cardKey)?.line;
    const card = perLine ? { key: cardKey, line: key } : { key: cardKey };
    const open = isOpen(openCards, stored, card);
    return {
      done: stampOf(stored, card),
      open,
      busy: writes.busy,
      onToggleOpen: () => setOpen(card, !open),
      onToggleDone: (done) => {
        if (done) setOpen(card, false);
        writes.mark(card, done);
      },
    };
  };
  const done = cards.filter((card) => stampOf(stored, card)).length;
  const allOpen = cards.every((card) => isOpen(openCards, stored, card));
  const pickRows = (mode) => {
    setRowsMode(mode);
    writeRowsPref(storage(), mode);
  };
  const fix = (item) => {
    if (item.fix?.tab) {
      onGoTab(item.fix.tab);
      return;
    }
    if (item.line) pickLine(item.line);
    const perLine = proposalMeta.cards.find((entry) => entry.key === item.fix.card)?.line;
    setOpen(perLine ? { key: item.fix.card, line: item.line || key } : { key: item.fix.card }, true);
    requestAnimationFrame(() => {
      document
        .querySelector(`[data-guide="build-${item.fix.card}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };
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
    recommendAll: writes.recommendAll,
    reasons: (text) => writes.setPath(`reasons.${key}`, text),
  };

  return (
    <div className="bnf-build" data-guide="proposal-builder">
      <BuilderToolbar
        progress={{ done, total: cards.length }}
        allOpen={allOpen}
        onAllOpen={(open) => setOpenCards((now) => ({ ...now, ...Object.fromEntries(cards.map((c) => [cardId(c), open])) }))}
        checks={data.checks}
        showChecks={showChecks}
        onShowChecks={setShowChecks}
        ready={data.ready}
        onFix={fix}
      />
      <LineTabs
        lines={data.lines}
        line={key}
        busy={writes.busy}
        onPick={pickLine}
        onMove={(lineKey, dir) => {
          const order = lineOrder(data.lines, lineKey, dir);
          if (order) writes.setPath('order', order);
        }}
      />
      {line.state === 'presented' ? (
        <IncumbentCard line={line} card={cardProps('quotes')} strip={strip} onEditIntent={() => onGoTab('intake')} />
      ) : (
        <PlansCard
          dealId={dealId}
          line={line}
          card={cardProps('quotes')}
          rowsMode={rowsMode}
          onRowsMode={pickRows}
          notice={
            <OffNotice
              line={line}
              busy={writes.busy}
              onOpenIntent={() => onGoTab('intake')}
              onPutOn={(hasToday) => writes.putOn(key, hasToday)}
            />
          }
          strip={line.off ? null : strip}
          busy={writes.busy}
          actions={actions}
        />
      )}
      <RowsCard line={line} card={cardProps('rows')} meta={proposalMeta} busy={writes.busy} onSet={writes.setPath} />
    </div>
  );
}
