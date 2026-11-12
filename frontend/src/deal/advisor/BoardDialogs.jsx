import * as q from '../../api/quotes';
import ActivityDrawer from '../../pages/DealPage/ActivityDrawer';
import PlanDialog from './PlanDialog';
import TemplateImport from './TemplateImport';

/*
 * The board's dialogs, one open at a time (`dialog`: {kind, plan?, preselect?}): 2V's plan dialog for ＋ Add plan and
 * Change role & links… (F134, until the Proposal grid's menu), the plan template import (F94), and the Activity drawer
 * the edit banner's "change history ▸" opens (F68). `counts` is not a dialog: the counts card opens above the board
 * (enrollment/EnrollmentPanel, slice 13); plans bought together open it with their ids picked.
 */
export default function BoardDialogs({ dealId, line, comparison, dialog, onDialog }) {
  const create = q.useCreatePlan(dealId);
  const update = q.useUpdatePlan(dealId);
  const importTemplate = q.useImportTemplate(dealId);
  const close = () => onDialog(null);
  const kind = dialog?.kind;
  return (
    <>
      <PlanDialog
        open={kind === 'plan'}
        onClose={close}
        line={line}
        plan={dialog?.plan ?? null}
        plans={comparison.plans}
        create={create}
        update={update}
        onBoughtTogether={(ids) => onDialog({ kind: 'counts', preselect: ids })}
      />
      <TemplateImport open={kind === 'import'} onClose={close} importTemplate={importTemplate} />
      <ActivityDrawer dealId={dealId} open={kind === 'activity'} onClose={close} />
    </>
  );
}
