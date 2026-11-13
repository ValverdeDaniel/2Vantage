import { useSearchParams } from 'react-router';
import { useClientAgenda } from '../../../api/clientPage';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import RefreshChip from '../../../ui/RefreshChip';
import AddTaskPanel from './AddTaskPanel';
import DealPanel from './DealPanel';
import DonePanel from './DonePanel';

/**
 * The client's Agenda (plan.md §8.5; CL24, I103 as Simplified; old Vantage 891f1b3 `radar/client/ClientAgendaTab.jsx`):
 * the title, "Add a task" on a deal, one panel per deal still being worked (Up next, Waiting on, Later and "All of this
 * deal's tasks ▸"), then Done. One read, `GET clients/{id}/agenda/`, whose panels are the deals' own Agendas; every
 * write is the deal's own door and refetches this page too. The old Coming up (reminders and client tasks), its
 * category chips and the reminders' Later wait with reminders (I104–I108). `?focus=task:<id>` flashes that row.
 */
export default function ClientAgendaTab({ client, meta }) {
  const query = useClientAgenda(client.id);
  const [params] = useSearchParams();
  if (query.isPending) return <Loading label="Loading the agenda…" />;
  if (query.isError) {
    return (
      <InlineError
        title="Could not load this client's agenda."
        error={query.error}
        onRetry={() => query.refetch()}
        retrying={query.isFetching}
      />
    );
  }
  const payload = query.data;
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
            Every task for this client: the tasks you add, and what each deal still being worked needs. Later brings any
            task back on the day you pick.
          </div>
        </div>
      </div>

      <AddTaskPanel clientId={client.id} panels={payload.deals} today={payload.today} meta={meta} />

      {payload.deals.length === 0 && (
        <div className="bb-panel">
          <div className="empty-state">Nothing scheduled: no deal is still being worked.</div>
        </div>
      )}
      {payload.deals.map((panel) => (
        <DealPanel
          key={panel.deal.id}
          clientId={client.id}
          panel={panel}
          today={payload.today}
          meta={meta}
          focus={params.get('focus')}
        />
      ))}

      <DonePanel clientId={client.id} panels={payload.deals} meta={meta} />
    </div>
  );
}
