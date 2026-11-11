import { useState } from 'react';
import { useReopenDeal, useUpdateDeal } from '../../api/deals';
import { LOST, manualStages, relationshipLabel } from '../../api/meta';
import { errorText } from '../../lib/errors';
import { formatDate } from '../../lib/format';
import Badge from '../../ui/Badge';
import Button from '../../ui/Button';
import Menu from '../../ui/Menu';
import SaveStatus from '../../ui/SaveStatus';
import VisuallyHidden from '../../ui/VisuallyHidden';
import ActivityDrawer from './ActivityDrawer';
import ClientDialog from './ClientDialog';
import styles from './DealHeader.module.css';
import EffectiveDate from './EffectiveDate';
import LinesPicker from './LinesPicker';
import LostDialog from './LostDialog';
import OwnerPicker from './OwnerPicker';
import StageStepper from './StageStepper';

// "Lost — <reason>" with Reopen. A lost deal stays editable (plan.md §3.6); only its stage waits for Reopen.
function LostBanner({ deal }) {
  const reopen = useReopenDeal(deal.id);
  return (
    <div className={styles.lostBanner} role="status">
      <span aria-hidden="true" className={styles.lostIcon}>
        ⊘
      </span>
      <p className={styles.lostText}>
        <strong>Lost</strong> — {deal.lost_reason}
        {deal.lost_at && <span className={styles.lostDate}> (marked lost {formatDate(deal.lost_at)})</span>}
      </p>
      {reopen.isError && (
        <span role="alert" className={styles.inlineError}>
          {errorText(reopen.error)}
        </span>
      )}
      <Button size="sm" onClick={() => reopen.mutate()} busy={reopen.isPending}>
        Reopen
      </Button>
    </div>
  );
}

// Stage ▾ — intake / quoting / proposal by hand (sold comes from marking a plan sold; lost from Mark lost).
function StageMenu({ deal, meta, update }) {
  const lost = deal.stage === LOST;
  return (
    <Menu
      label="Stage"
      ariaLabel="Set stage"
      align="end"
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

/**
 * Deal header (plan.md §8.4): client name (edit dialog), effective date, owner, actions, Lines, stage stepper,
 * lost banner. Every change goes through PATCH and refreshes the rest of the deal's queries.
 */
export default function DealHeader({ deal, meta }) {
  const [open, setOpen] = useState(null); // 'client' | 'lost' | 'activity'
  const stageUpdate = useUpdateDeal(deal.id);
  const lost = deal.stage === LOST;
  const close = () => setOpen(null);

  return (
    <header className={styles.header}>
      {lost && <LostBanner deal={deal} />}

      <div className={styles.topRow}>
        <div className={styles.facts}>
          <h1 className={styles.name}>
            <button type="button" className={styles.nameButton} onClick={() => setOpen('client')}>
              {deal.client.name}
              <span aria-hidden="true" className={styles.pencil}>
                ✎
              </span>
              <VisuallyHidden> (edit name and type)</VisuallyHidden>
            </button>
          </h1>
          <Badge tone="neutral">{relationshipLabel(meta, deal.client.relationship)}</Badge>
          <span aria-hidden="true" className={styles.sep}>
            ·
          </span>
          <EffectiveDate deal={deal} />
          <span aria-hidden="true" className={styles.sep}>
            ·
          </span>
          <OwnerPicker deal={deal} />
        </div>
        <div className={styles.actions}>
          <Button variant="ghost" onClick={() => setOpen('activity')}>
            Activity
          </Button>
          <StageMenu deal={deal} meta={meta} update={stageUpdate} />
          {!lost && <Button onClick={() => setOpen('lost')}>Mark lost</Button>}
        </div>
      </div>

      <LinesPicker deal={deal} meta={meta} />

      <div className={styles.stageRow}>
        <StageStepper stage={deal.stage} meta={meta} />
        <SaveStatus mutation={stageUpdate} />
      </div>

      {open === 'client' && <ClientDialog deal={deal} meta={meta} onClose={close} />}
      {open === 'lost' && <LostDialog deal={deal} onClose={close} />}
      <ActivityDrawer dealId={deal.id} open={open === 'activity'} onClose={close} />
    </header>
  );
}
