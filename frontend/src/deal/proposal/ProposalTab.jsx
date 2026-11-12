import { useState } from 'react';
import { useProposal, useSaveProposal } from '../../api/proposals';
import { useSetRecommended } from '../../api/quotes';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import RefreshChip from '../../ui/RefreshChip';
import SaveStatus from '../../ui/SaveStatus';
import { useToast } from '../../ui/useToast';
import ProposalLine from './ProposalLine';

// A typed box of the old builder (`bnf-build-words`): saved when it loses focus, if it changed.
function SavedText({ label, value, onSave, multiline }) {
  const [draft, setDraft] = useState(null);
  const props = {
    value: draft ?? value,
    onChange: (event) => setDraft(event.target.value),
    onBlur: () => {
      if (draft !== null && draft !== value) onSave(draft);
      setDraft(null);
    },
  };
  return (
    <label>
      <span>{label}</span>
      {multiline ? <textarea rows={2} {...props} /> : <input type="text" {...props} />}
    </label>
  );
}

// "Issue to client", in the old Proposal packet card's look (ProposalPacketCard.jsx at 891f1b3).
function IssueCard({ blockers, hasLines }) {
  return (
    <section className="bb-panel bnf-build-panel bnf-bcard bnf-packet-card" aria-label="Issue to client">
      <div className="bnf-bcard-head">
        <span className="bb-panel-title">Issue to client</span>
        {!blockers.length && hasLines && (
          <span className="bnf-bcard-summary">Every current plan has a recommendation.</span>
        )}
        <span className="bnf-bcard-mark">
          <Button size="sm" variant="primary" disabled title="The client workbook (M7) and issuing (M8) come next">
            Issue to client
          </Button>
        </span>
      </div>
      {blockers.length > 0 && (
        <div className="bnf-build-checks" role="region" aria-label="Not ready to issue">
          <div className="bnf-build-checks-head">
            <b>Not ready to issue:</b>
          </div>
          <ul className="bnf-build-checks-list">
            {blockers.map((blocker) => (
              <li key={blocker} className="bnf-build-check bnf-build-check-stop">
                <span className="bnf-build-check-msg">{blocker}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="bnf-packet-note">The client workbook and issuing arrive in the next slices (M7–M8).</div>
    </section>
  );
}

/**
 * The Proposal tab (plan.md §8.15): 2V's selection and preview until slice 25 retires them — what each line presents,
 * the firm's recommendation and why, and a preview of exactly what the client workbook will print — on the old
 * proposal builder's cards. The workbook itself (M7) and issuing it (M8) come next.
 */
export default function ProposalTab({ deal }) {
  const toast = useToast();
  const proposal = useProposal(deal.id);
  const save = useSaveProposal(deal.id);
  const recommend = useSetRecommended(deal.id);

  if (proposal.isPending) return <Loading label="Loading the proposal…" />;
  if (proposal.isError) {
    return <InlineError title="Proposal" error={proposal.error} onRetry={() => proposal.refetch()} />;
  }
  const data = proposal.data;
  const saveField = (changes) => save.mutateAsync(changes).catch((error) => toast.error(errorText(error)));

  return (
    <div className="bb-tab-page">
      <div className="bb-sov-header">
        <div>
          <div className="bb-tab-title">
            Proposal
            <RefreshChip loading={proposal.isFetching} label="Refreshing…" />
          </div>
          <div className="bb-subtitle">
            What each line presents, our recommendation and why, and a preview of exactly what the client workbook
            will print.
          </div>
        </div>
      </div>

      <div className="bnf-build">
        <IssueCard blockers={data.issue_blockers} hasLines={data.lines.length > 0} />

        <section className="bb-panel bnf-build-panel" aria-label="Title and notes">
          <div className="bnf-build-words">
            <SavedText label="Title" value={data.title} onSave={(title) => saveField({ title })} />
            <SavedText label="Notes" value={data.notes} multiline onSave={(notes) => saveField({ notes })} />
          </div>
          <SaveStatus mutation={save} />
        </section>

        {!data.lines.length && (
          <div className="bb-panel">
            <div className="bb-panel-title">Nothing to present yet</div>
            <div className="bb-panel-sub">
              Add plans to the deal&apos;s lines in the Advisor; each requested line with plans appears here.
            </div>
          </div>
        )}
        {data.lines.map((line) => (
          <ProposalLine
            key={line.line}
            line={line}
            reasons={data.reasons?.[line.line]}
            save={save}
            recommend={recommend}
          />
        ))}
      </div>
    </div>
  );
}
