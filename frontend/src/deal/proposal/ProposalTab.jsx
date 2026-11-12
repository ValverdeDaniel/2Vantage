import { useNavigate } from 'react-router';
import { useProposal } from '../../api/proposals';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import RefreshChip from '../../ui/RefreshChip';
import PacketCard from './packet/PacketCard';

/*
 * The Proposal tab (plan.md §8.15; J70, J96–J104; the old close/ComparisonGrid.jsx head at 891f1b3): "Plan comparison"
 * with its refresh chip, then the Proposal packet (everything that leaves the building: the checks, the draft
 * downloads, Issue to client and the issued versions), then `board`: the Advisor's board in presented mode, which
 * the route hands in (pages/DealPage/ProposalRoute.jsx), so neither folder imports the other (J.3.6). The packet card
 * reads the builder's payload (its checks, readiness and issues), ['deal', id, 'proposal'] with staleTime 0.
 */
export default function ProposalTab({ deal, board = null }) {
  const navigate = useNavigate();
  const proposal = useProposal(deal.id);
  const advisor = (view) => navigate(`/deals/${deal.id}/advisor?view=${view}`);

  let packet;
  if (proposal.isPending) packet = <Loading label="Loading the proposal…" />;
  else if (proposal.isError && !proposal.data) {
    packet = <InlineError title="Proposal" error={proposal.error} onRetry={() => proposal.refetch()} />;
  } else {
    packet = (
      <PacketCard
        dealId={deal.id}
        proposal={proposal.data}
        onOpenBuilder={() => advisor('build')}
        onOpenProposal={() => advisor('export')}
      />
    );
  }
  return (
    <div className="bb-tab-page">
      <div className="bb-sov-header">
        <div>
          <div className="bb-tab-title">
            Plan comparison
            <RefreshChip
              loading={Boolean(proposal.data) && proposal.isFetching}
              error={Boolean(proposal.data) && proposal.isError}
              onRetry={() => proposal.refetch()}
            />
          </div>
          <div className="bb-subtitle">
            Normalized from the carrier quotes — plans as columns, benefits as rows. Click any cell to edit. Coloured
            cells need attention.
          </div>
        </div>
      </div>
      {packet}
      {board}
    </div>
  );
}
