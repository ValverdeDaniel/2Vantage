import { Link } from 'react-router';
import { AgendaSections, useAgendaActions } from '../../../deal/agenda';
import ConfirmDialog from '../../../ui/ConfirmDialog';
import { PANEL_SECTIONS, panelSub, panelTitle } from './agendaView';

/**
 * One deal still being worked, on the client's Agenda (plan.md §8.5; CL24; old 891f1b3 `ClientAgendaTab.jsx`'s deal
 * panels): "Deal renewing <date> · <stage>", what it needs next, "All of this deal's tasks ▸" to its own Agenda, then
 * its Up next, Waiting on and Later sections, every button wired to the deal's own doors (marks, tasks, nudges) as on
 * the deal's tab. `focus` (`?focus=task:12`) flashes a row the panel holds (I7).
 */
export default function DealPanel({ clientId, panel, today, meta, focus }) {
  const { deal } = panel;
  const actions = useAgendaActions(deal.id, { clientId });
  const confirm = actions.confirm;
  const title = panelTitle(deal, meta);
  return (
    <section className="bb-panel" aria-label={title}>
      <div className="bnf-cw-agenda-head">
        <div>
          <div className="bb-panel-title">{title}</div>
          <div className="bb-panel-sub">{panelSub(panel)}</div>
        </div>
        <Link className="bnf-agenda-open" to={deal.link}>
          All of this deal&apos;s tasks ▸
        </Link>
      </div>
      <AgendaSections
        payload={{ today, rows: panel.rows }}
        meta={meta}
        focus={focus}
        actions={actions}
        only={PANEL_SECTIONS}
      />
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
    </section>
  );
}
