import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useQuotedFiles } from '../../api/asQuoted';
import { useMeta } from '../../api/meta';
import * as q from '../../api/quotes';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import RefreshChip from '../../ui/RefreshChip';
import { ExportViewer, PagesView, ProposalBuilder } from '../proposal';
import AsQuotedView from './AsQuotedView';
import BoardDialogs from './BoardDialogs';
import EnrollmentPanel from './enrollment/EnrollmentPanel';
import LineTabs from './LineTabs';
import QuoteBoard from './board/QuoteBoard';
import PackagesPanel from './PackagesPanel';
import useAdvisorPrefs from './useAdvisorPrefs';
import ViewPills from './ViewPills';
import { AddQuotesButton } from '../claude'; // Work with Claude's door on the board (F96; slice 20)

/*
 * The Advisor (plan.md §8.14; F1, F2, F5–F8; the old close/AdvisorTab.jsx, split by responsibility): the title and
 * its subtitle, the view pills, and the view on screen — today the Quote comparison (board/QuoteBoard). The first
 * load shows the old load panel with how many plans are coming; a refetch keeps the board on screen with the
 * Refreshing chip (§8.22). Queries are ['deal', id, 'advisor', …] with staleTime 0. The finder, filters and saved
 * setups (slice 10) are the board's filter card, above its header; the counts card and the enrollment notices
 * (slice 13) sit between the board's header and its table. ▦ Pages mounts the proposal folder's PagesView in the
 * table's place (slice 14; F37), kept per browser. The Proposal builder view mounts the proposal folder's builder
 * (slice 25; J17), on the line the Advisor shows. "As quoted" shows one scanned quote as printed (F42; slice 21),
 * offered once a read has landed a printed table. The Export viewer, last, mounts the proposal folder's viewer (slice
 * 28; F3, F136): its file is kept with the view and line, and where it stands in each file (`exportPlace`) is held
 * here, so a switch to the builder and back finds the same tab; "Open proposal ▸" on the builder opens it (J27), and
 * "See the slides ▸" on its Plans card opens the PowerPoint on that line's first plan set (J58; slice 30).
 */

function EmptyPanel({ title, children, actions }) {
  return (
    <div className="bb-panel">
      <div className="bb-panel-title">{title}</div>
      <div className="bb-panel-sub">{children}</div>
      {actions}
    </div>
  );
}

const PAGES_INTRO = (
  <div className="bb-panel-sub">
    What the client will see: each block is one comparison page of the PowerPoint, columns left to right. Click a plan
    name to change it; the arrows reorder. The Columns tabs above pick the rows.
  </div>
);

export default function AdvisorTab({ deal }) {
  const { data: meta } = useMeta();
  const navigate = useNavigate();
  const lines = q.useAdvisorLines(deal.id);
  const quoted = useQuotedFiles(deal.id);
  const prefs = useAdvisorPrefs(lines.data ?? [], quoted.data);
  const comparison = q.useComparison(deal.id, prefs.line);
  const [dialog, setDialog] = useState(null);
  const [exportPlace, setExportPlace] = useState({});
  const packages = {
    create: q.useCreatePackage(deal.id),
    update: q.useUpdatePackage(deal.id),
    remove: q.useDeletePackage(deal.id),
  };

  const data = comparison.data;
  const head = (
    <div className="bb-sov-header">
      <div>
        <div className="bb-tab-title">
          Quote advisor
          <RefreshChip
            label="Refreshing quotes…"
            loading={Boolean(data) && comparison.isFetching}
            error={Boolean(data) && comparison.isError}
            onRetry={() => comparison.refetch()}
          />
        </div>
        <div className="bb-subtitle">
          Narrow the quoted plans with the triggers below, star the ones to present and put them in the order the
          client will see. Shortlisted plans drive the client proposal.
        </div>
      </div>
    </div>
  );

  if (lines.isPending || !meta) return <Loading label="Loading the quotes…" />;
  if (lines.isError) {
    return <InlineError title="Quote advisor" error={lines.error} onRetry={() => lines.refetch()} />;
  }

  const row = lines.data.find((r) => r.line === prefs.line);
  const count = row ? row.current + row.renewal + row.alternate : 0;
  let body;
  if (prefs.view === 'build') {
    body = (
      <div className="bnf-advisor-tab-split">
        <ProposalBuilder
          dealId={deal.id}
          meta={meta}
          line={prefs.line}
          onLine={prefs.pickLine}
          onQuotes={() => prefs.pickView('quotes')}
          onGoTab={(tab) => navigate(`/deals/${deal.id}/${tab}`)}
          onExport={() => prefs.pickView('export')}
          onSlides={() => {
            setExportPlace((now) => ({ ...now, deck: { line: prefs.line } }));
            prefs.openExport('powerpoint');
          }}
        />
      </div>
    );
  } else if (prefs.view === 'export') {
    body = (
      <div className="bnf-advisor-tab-split">
        <ExportViewer
          dealId={deal.id}
          file={prefs.file}
          onFile={prefs.pickFile}
          place={exportPlace}
          onPlace={setExportPlace}
          onGoBuild={() => prefs.pickView('build')}
        />
      </div>
    );
  } else if (prefs.view === 'quoted') {
    body = <AsQuotedView deal={deal} meta={meta} files={quoted.data ?? []} line={prefs.line} />;
  } else if (!lines.data.length) {
    body = (
      <EmptyPanel
        title="No lines to quote yet"
        actions={
          <span className="bnf-count-actions">
            <AddQuotesButton primary />
          </span>
        }
      >
        Add the lines to quote in the deal header (Lines), then add plans here — or add the carrier quotes, and Claude
        adds the lines they quote.
      </EmptyPanel>
    );
  } else if (!data && comparison.isError) {
    body = <InlineError title="Quote advisor" error={comparison.error} onRetry={() => comparison.refetch()} />;
  } else if (!data) {
    // The line tabs stay while another line's plans load, so a switch never loses them.
    body = (
      <>
        <LineTabs lines={lines.data} line={prefs.line} onPick={prefs.pickLine} />
        <Loading
          label={count ? `Loading ${count} quoted plan${count === 1 ? '' : 's'}…` : 'Loading the quotes…'}
          note={count > 50 ? 'A deal this size takes a few seconds the first time; coming back to it is instant.' : null}
        />
      </>
    );
  } else if (!data.plans.length) {
    body = (
      <>
      <LineTabs lines={lines.data} line={prefs.line} onPick={prefs.pickLine} />
      <EmptyPanel
        title="No quoted plans yet"
        actions={
          <span className="bnf-count-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={() => setDialog({ kind: 'plan', plan: null })}>
              ＋ Add plan
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setDialog({ kind: 'import' })}>
              ⤒ Import from template
            </button>
            <AddQuotesButton />
          </span>
        }
      >
        Add the carrier quotes here, or bring them in from a filled plan template — the comparison feeds this page.
      </EmptyPanel>
      </>
    );
  } else {
    const counts = dialog?.kind === 'counts';
    const lineLabel = meta.lines.find((entry) => entry.key === prefs.line)?.label ?? prefs.line;
    const panel = (
      <EnrollmentPanel
        dealId={deal.id}
        meta={meta}
        line={prefs.line}
        lineLabel={lineLabel}
        data={data}
        open={counts}
        preselect={dialog?.preselect}
        onOpen={() => setDialog({ kind: 'counts' })}
        onClose={() => setDialog(null)}
      />
    );
    const pages = {
      on: prefs.layout === 'pages',
      pick: prefs.pickLayout,
      render: (preset) => (
        <PagesView dealId={deal.id} line={prefs.line} lineLabel={lineLabel} preset={preset} intro={PAGES_INTRO} />
      ),
    };
    body = (
      <>
        <QuoteBoard
          deal={deal}
          meta={meta}
          lines={lines.data}
          line={prefs.line}
          onLine={prefs.pickLine}
          data={data}
          prefs={prefs}
          onDialog={setDialog}
          enrollment={{ open: counts, panel }}
          pages={pages}
        />
        <PackagesPanel comparison={data} create={packages.create} update={packages.update} remove={packages.remove} />
      </>
    );
  }

  return (
    <div className="bb-tab-page">
      {head}
      <ViewPills views={prefs.offered} view={prefs.view} onPick={prefs.pickView} />
      {body}
      {data && (
        <BoardDialogs dealId={deal.id} line={prefs.line} comparison={data} dialog={dialog} onDialog={setDialog} />
      )}
    </div>
  );
}
