import { useSearchParams } from 'react-router';
import { useAgenda } from '../../api/agenda';
import { useMeta } from '../../api/meta';
import ConfirmDialog from '../../ui/ConfirmDialog';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import RefreshChip from '../../ui/RefreshChip';
import AgendaSections from './AgendaSections';
import TaskForm from './TaskForm';
import useAgendaActions from './useAgendaActions';

/*
 * The deal's Agenda tab (plan.md §8.7; I1–I8, I27): every task on the deal — the steps it needs, worked out from every
 * section's facts, and the tasks people add — by where each stands. Old Vantage 891f1b3 `shared/DealAgendaTab.jsx`:
 * its title, subtitle, "Add a task" panel and sections, its words and classes. `?focus=task:<id>` flashes one row.
 */
export default function AgendaTab({ deal }) {
  const meta = useMeta().data;
  const query = useAgenda(deal.id);
  const actions = useAgendaActions(deal.id);
  const [params] = useSearchParams();
  const payload = query.data;

  if (query.isPending || !meta) return <Loading label="Loading the agenda…" />;
  if (query.isError) {
    return (
      <InlineError
        title="Could not load this deal's agenda."
        error={query.error}
        onRetry={() => query.refetch()}
        retrying={query.isFetching}
      />
    );
  }
  const confirm = actions.confirm;

  return (
    <div className="bb-tab-page">
      <div className="bnf-ov-titlerow">
        <div>
          <div className="bb-tab-title">
            Agenda
            <RefreshChip
              loading={query.isFetching && !query.isPending}
              error={query.isRefetchError}
              onRetry={() => query.refetch()}
            />
          </div>
          <div className="bb-subtitle">
            Every task on this deal: what the deal needs next, what we are waiting on, and the tasks you add. Done works
            itself out when the work is done; Later brings a task back on the day you pick.
          </div>
        </div>
      </div>

      <div className="bb-panel">
        <div className="bb-panel-title">Add a task</div>
        <TaskForm today={payload.today} busy={actions.busy === 'add'} onSave={actions.addTask} />
      </div>

      <div className="bb-panel">
        <AgendaSections payload={payload} meta={meta} focus={params.get('focus')} actions={actions} />
      </div>

      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm?.title}
        message={confirm?.message}
        confirmLabel={confirm?.label}
        tone={confirm?.danger ? 'danger' : 'primary'}
        onCancel={actions.closeConfirm}
        onConfirm={() => {
          const go = confirm.go;
          actions.closeConfirm();
          go();
        }}
      />
    </div>
  );
}
