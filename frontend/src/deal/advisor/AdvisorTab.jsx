import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { useMeta } from '../../api/meta';
import * as q from '../../api/quotes';
import { downloadFile } from '../../lib/download';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import cx from '../../ui/cx';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import Menu from '../../ui/Menu';
import RefreshChip from '../../ui/RefreshChip';
import { useToast } from '../../ui/useToast';
import EnrollmentCard from './EnrollmentCard';
import PackagesPanel from './PackagesPanel';
import PlanDialog from './PlanDialog';
import PlanTable from './PlanTable';
import TemplateImport from './TemplateImport';

// The old empty Advisor (AdvisorTab.jsx at 891f1b3): a panel with a title and a grey line.
function EmptyPanel({ title, children }) {
  return (
    <div className="bb-panel">
      <div className="bb-panel-title">{title}</div>
      <div className="bb-panel-sub">{children}</div>
    </div>
  );
}

/**
 * The Advisor (plan.md §8.14): 2V's simplified Advisor (F134) until slice 9 replaces it — every plan on a line side
 * by side, priced by the server, in the old Proposal grid's look. Its queries live under ['deal', id, 'advisor', …]
 * with staleTime 0.
 */
export default function AdvisorTab({ deal }) {
  const toast = useToast();
  const { data: meta } = useMeta();
  const [params, setParams] = useSearchParams();
  const lines = q.useAdvisorLines(deal.id);
  const line = params.get('line') || lines.data?.[0]?.line || '';
  const comparison = q.useComparison(deal.id, line);
  const [hideEmpty, setHideEmpty] = useState(false);
  const [planDialog, setPlanDialog] = useState(null); // {plan: null | plan}
  const [enrollment, setEnrollment] = useState(null); // {preselect: [ids]}
  const [importing, setImporting] = useState(false);

  const mutations = {
    create: q.useCreatePlan(deal.id),
    update: q.useUpdatePlan(deal.id),
    remove: q.useDeletePlan(deal.id),
    createRenewal: q.useCreateRenewal(deal.id),
    copy: q.useCopyPlan(deal.id),
    sold: q.useSetSold(deal.id),
    recommend: q.useSetRecommended(deal.id),
    star: q.useStar(deal.id),
    order: q.useOrderPlans(deal.id),
    enrollment: q.useSaveEnrollment(deal.id),
    createPackage: q.useCreatePackage(deal.id),
    updatePackage: q.useUpdatePackage(deal.id),
    deletePackage: q.useDeletePackage(deal.id),
    importTemplate: q.useImportTemplate(deal.id),
  };

  const fieldsByKey = useMemo(
    () => Object.fromEntries((meta?.plans?.fields ?? []).map((field) => [field.key, field])),
    [meta],
  );

  const actions = {
    ...mutations,
    editLinks: (plan) => setPlanDialog({ plan }),
    move: (plan, direction) => {
      const peers = comparison.data.plans.filter((p) => p.role === plan.role).map((p) => p.id);
      const index = peers.indexOf(plan.id);
      const target = index + direction;
      if (target < 0 || target >= peers.length) return;
      [peers[index], peers[target]] = [peers[target], peers[index]];
      mutations.order
        .mutateAsync({ line, role: plan.role, plan_ids: peers })
        .catch((error) => toast.error(errorText(error)));
    },
  };

  async function download(scope) {
    try {
      await downloadFile(q.templateUrl(deal.id, scope === 'line' ? line : ''));
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  if (lines.isPending) return <Loading label="Loading the quotes…" />;
  if (lines.isError) {
    return <InlineError title="Quote advisor" error={lines.error} onRetry={() => lines.refetch()} />;
  }

  const data = comparison.data;
  return (
    <div className="bb-tab-page">
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
            Plans as columns, benefits as rows. Click any cell to edit. Coloured cells need attention.
          </div>
        </div>
      </div>

      {!lines.data.length ? (
        <EmptyPanel title="No lines to quote yet">
          Add the lines to quote in the deal header (Lines), then add plans here.
        </EmptyPanel>
      ) : (
        <>
          <nav className="bnf-lineswitch" aria-label="Lines of coverage">
            {lines.data.map((row) => (
              <button
                key={row.line}
                type="button"
                aria-current={row.line === line ? 'true' : undefined}
                className={cx('bnf-linetab', row.line === line && 'bnf-linetab-on')}
                onClick={() => setParams({ line: row.line })}
                title={`${row.current} current · ${row.renewal} renewal · ${row.alternate} alternate`}
              >
                {row.label}
                <span className="bnf-linetab-count">
                  {row.current}·{row.renewal}·{row.alternate}
                </span>
                {row.recommendation_covered && (
                  <span className="bnf-linetab-done" aria-label="Every current plan has a recommendation">
                    ✓
                  </span>
                )}
              </button>
            ))}
          </nav>

          <div className="bb-sov-toolbar bnf-grid-toolbar">
            <label className="bnf-filter-check">
              <input type="checkbox" checked={hideEmpty} onChange={(event) => setHideEmpty(event.target.checked)} />
              Hide empty rows
            </label>
            <div className="bb-toolbar-actions">
              <Menu
                label="Template"
                items={[
                  { key: 'line', label: 'Download plan template (this line)', onSelect: () => download('line') },
                  { key: 'all', label: 'Download plan template (all lines)', onSelect: () => download('all') },
                  { key: 'import', label: 'Import plan template…', onSelect: () => setImporting(true) },
                ]}
              />
              <Button size="sm" onClick={() => setEnrollment({ preselect: [] })} disabled={!data?.plans.length}>
                Enrollment
              </Button>
              <Button size="sm" variant="primary" onClick={() => setPlanDialog({ plan: null })}>
                ＋ Plan
              </Button>
            </div>
          </div>

          {comparison.isError && !data && (
            <InlineError compact error={comparison.error} onRetry={() => comparison.refetch()} />
          )}
          {!data && comparison.isPending && <Loading label="Loading the quotes…" />}
          {data?.warnings?.map((warning) => (
            <div key={warning.code} className="bnf-tiersource-note bnf-tiersource-none" role="status">
              ⚠ {warning.message}
            </div>
          ))}
          {data && !data.plans.length && (
            <EmptyPanel title="No plans on this line yet">Add a plan, or import the plan template.</EmptyPanel>
          )}
          {data && data.plans.length > 0 && (
            <>
              <PlanTable comparison={data} fieldsByKey={fieldsByKey} hideEmpty={hideEmpty} actions={actions} />
              <PackagesPanel
                comparison={data}
                create={mutations.createPackage}
                update={mutations.updatePackage}
                remove={mutations.deletePackage}
              />
            </>
          )}
        </>
      )}

      <PlanDialog
        open={Boolean(planDialog)}
        onClose={() => setPlanDialog(null)}
        line={line}
        plan={planDialog?.plan ?? null}
        plans={data?.plans ?? []}
        create={mutations.create}
        update={mutations.update}
        onBoughtTogether={(ids) => setEnrollment({ preselect: ids })}
      />
      {data && (
        <EnrollmentCard
          open={Boolean(enrollment)}
          onClose={() => setEnrollment(null)}
          comparison={data}
          preselect={enrollment?.preselect}
          save={mutations.enrollment}
        />
      )}
      <TemplateImport open={importing} onClose={() => setImporting(false)} importTemplate={mutations.importTemplate} />
    </div>
  );
}
