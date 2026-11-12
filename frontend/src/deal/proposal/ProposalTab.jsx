import { useNavigate } from 'react-router';
import { useProposal } from '../../api/proposals';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import RefreshChip from '../../ui/RefreshChip';

/*
 * The Proposal tab (plan.md §8.15) until slice 32 makes it the Advisor's board in presented mode with the packet card.
 * 2V's selection and preview retired in slice 25: the proposal is built in the Advisor's "Proposal builder" view, and
 * this tab says whether it is ready to issue — the builder's own answer (`ready`), in the old packet card's look —
 * with the way there. Issuing arrives with slice 32.
 */
export default function ProposalTab({ deal }) {
  const navigate = useNavigate();
  const proposal = useProposal(deal.id);

  if (proposal.isPending) return <Loading label="Loading the proposal…" />;
  if (proposal.isError && !proposal.data) {
    return <InlineError title="Proposal" error={proposal.error} onRetry={() => proposal.refetch()} />;
  }
  const { ready, lines } = proposal.data;
  return (
    <div className="bb-tab-page">
      <div className="bb-sov-header">
        <div>
          <div className="bb-tab-title">
            Proposal
            <RefreshChip loading={proposal.isFetching} label="Refreshing…" />
          </div>
          <div className="bb-subtitle">
            Build the proposal in the Advisor: which plans each line presents, our recommendation and why, and what each
            section shows.
          </div>
        </div>
      </div>
      <section className="bb-panel bnf-build-panel bnf-bcard bnf-packet-card" aria-label="Issue to client">
        <div className="bnf-bcard-head">
          <span className="bb-panel-title">Issue to client</span>
          {ready.ok && <span className="bnf-bcard-summary">Every marketed line has a recommendation.</span>}
          <span className="bnf-bcard-mark">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => navigate(`/deals/${deal.id}/advisor?view=build`)}
            >
              Open the proposal builder ▸
            </button>
          </span>
        </div>
        {!lines.length && <div className="bnf-packet-note">Nothing to present yet: add plans in the Advisor.</div>}
        {ready.sentence && (
          <div className="bnf-build-ready" role="status">
            {ready.sentence}
          </div>
        )}
        <div className="bnf-packet-note">Issuing the PDF, PowerPoint and workbook arrives with the client files.</div>
      </section>
    </div>
  );
}
