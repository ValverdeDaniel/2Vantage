import { useState } from 'react';
import { useUpdateDeal } from '../../api/deals';
import { LOST, manualStages, relationshipLabel, stageLabel } from '../../api/meta';
import { initialsOf, stagePillClass, statusBadgeClass } from '../../lib/dealLook';
import { formatDate, formatMoney } from '../../lib/format';
import Menu from '../../ui/Menu';
import SaveStatus from '../../ui/SaveStatus';
import ActivityDrawer from './ActivityDrawer';
import ClientDialog from './ClientDialog';
import EffectiveDate from './EffectiveDate';
import HeaderFact from './HeaderFact';
import LinesPicker from './LinesPicker';
import OwnerPicker from './OwnerPicker';

// Stage ▾ — intake, quoting or proposal by hand (A30); sold comes from marking a plan sold, lost from Mark as lost.
function StageMenu({ deal, meta, update }) {
  const lost = deal.stage === LOST;
  return (
    <Menu
      label="Stage"
      ariaLabel="Set stage"
      disabled={lost}
      title={lost ? 'Reopen the deal to change its stage.' : undefined}
      items={manualStages(meta).map((stage) => ({
        key: stage.key,
        label: stage.label,
        checked: deal.stage === stage.key,
        onSelect: () => {
          if (stage.key !== deal.stage) update.mutate({ stage: stage.key });
        },
      }))}
    />
  );
}

// A typed deal size edits as plain dollars: '250000.00' → '250000'.
function sizeDraft(value) {
  return value ? value.replace(/\.00$/, '') : '';
}

/**
 * The header strip on every tab (plan.md §8.4; new against the old app, M112), built from the old Overview header's
 * classes (bnf-ov-*): the client's name (opens the client dialog until slice 67) and status, the stage pill with
 * Stage ▾ ("Lost" shows here on every tab), the effective date, the owner, the Potential deal size and the Agent of
 * record (M27, M29), Lines and Activity with Revert. Mark as lost… and Archive… with their banners live on the
 * Overview from slice 62 (M1, M112). Every change goes through PATCH and refreshes the rest of the deal's queries.
 */
export default function DealHeader({ deal, meta }) {
  const [open, setOpen] = useState(null); // 'client' | 'activity'
  const stageUpdate = useUpdateDeal(deal.id);
  const close = () => setOpen(null);
  const { client } = deal;

  return (
    <div className="bb-panel bnf-ov-header">
      <div className="bnf-ov-identity">
        <div className="bb-avatar bnf-ov-avatar" aria-hidden="true">
          {initialsOf(client.name)}
        </div>
        <div className="bnf-ov-identity-main">
          <button
            type="button"
            className="bnf-ov-name bnf-wq-namebtn"
            title="Edit the client's name and status"
            onClick={() => setOpen('client')}
          >
            {client.name}
          </button>
          <div className="bnf-ov-chips">
            <span className={statusBadgeClass(client.relationship)} title="Client status">
              {relationshipLabel(meta, client.relationship)}
              {client.client_since ? ` · since ${formatDate(client.client_since)}` : ''}
            </span>
            <span className={stagePillClass(deal.stage)} title="Deal stage">
              {stageLabel(meta, deal.stage)}
            </span>
            <SaveStatus mutation={stageUpdate} />
            <EffectiveDate deal={deal} />
            <OwnerPicker deal={deal} />
            <HeaderFact
              deal={deal}
              field="deal_size"
              label="Potential deal size"
              shown={formatMoney(deal.deal_size)}
              initial={sizeDraft(deal.deal_size)}
              placeholder="$ amount"
            />
            <HeaderFact
              deal={deal}
              field="agent_of_record"
              label="Agent of record"
              shown={deal.agent_of_record}
              fallback={deal.agent_default ? `${deal.agent_default} (default)` : ''}
              initial={deal.agent_of_record}
              placeholder={deal.agent_default || 'Agent name'}
              hint="Who the carrier forms print as the agent. Blank prints the owner, else the agency's producer."
            />
          </div>
        </div>
        <div className="bnf-ov-titlebtns">
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setOpen('activity')}>
            Activity
          </button>
          <StageMenu deal={deal} meta={meta} update={stageUpdate} />
        </div>
      </div>
      <div className="bnf-ov-facts">
        <LinesPicker deal={deal} meta={meta} />
      </div>
      {open === 'client' && <ClientDialog deal={deal} meta={meta} onClose={close} />}
      <ActivityDrawer dealId={deal.id} open={open === 'activity'} onClose={close} />
    </div>
  );
}
