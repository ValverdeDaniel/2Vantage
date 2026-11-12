import { PresentedBoard } from '../../deal/advisor';
import ProposalTab from '../../deal/proposal';

/*
 * The Proposal tab as the route composes it (plan.md §8.15; J.3.6, ch31): the proposal folder's tab (its title and
 * the packet card) with the Advisor's board in presented mode under it. Composed here, so neither tab folder imports
 * the other (the Advisor already mounts the proposal folder's builder, Pages and Export viewer).
 */
export default function ProposalRoute({ deal }) {
  return <ProposalTab deal={deal} board={<PresentedBoard deal={deal} />} />;
}
