import { useNavigate } from 'react-router';
import { useDiscardRead, useJob } from '../../api/ai';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { claudeDoor } from './door';
import { censusReadHead } from './readWords';

/*
 * A census read waiting for review (plan.md §10.5; C9, D29, D74; slice 51). Its people wait on the Census tab as a
 * staged import, in the mapping dialog with its dry run, so this card only says what was read and hands over: the old
 * banner's "A census file is waiting for review … read, not applied — nothing on the roster has changed. Review it ▸",
 * pointing the other way. Discard sets the import aside with the read. Nothing here names a person.
 */
export default function CensusReadCard({ dealId, jobId, nameOf }) {
  const toast = useToast();
  const navigate = useNavigate();
  const job = useJob(jobId);
  const discard = useDiscardRead(dealId);
  const changeSet = job.data?.result;
  const item = changeSet?.items?.[0];
  if (!item) return null;

  async function drop() {
    try {
      await discard.mutateAsync(jobId);
      toast.success('Read discarded. Nothing on the roster changed.');
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <div className="bnf-staged-review bb-mt" data-review-job={jobId} data-census-import={item.import}>
      <div className="bnf-staged-head">
        <div>
          <div className="bb-panel-title">A census file is waiting for review</div>
          <div className="bb-panel-sub">{censusReadHead(item, nameOf(changeSet.documents?.[0]))}</div>
        </div>
        <div className="bnf-staged-actions">
          <button type="button" className="btn btn-secondary btn-sm" disabled={discard.isPending} onClick={drop}>
            Discard
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => {
              claudeDoor.close(); // the mapping dialog is the next step: the drawer would cover it
              navigate(`/deals/${dealId}/census?import=${item.import}`);
            }}
          >
            Review it on the Census tab ▸
          </button>
        </div>
      </div>
      {changeSet.findings?.length > 0 && (
        <div className="bnf-staged-section">
          <div className="bnf-staged-section-title">Worth a look</div>
          <ul className="bnf-staged-list">
            {changeSet.findings.map((finding) => (
              <li key={finding.text}>{finding.text}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
