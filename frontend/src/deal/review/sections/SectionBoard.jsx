import { useSection } from '../../../api/reviewForm';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import CensusBoard from './CensusBoard';
import IntakeBoard from './IntakeBoard';

/*
 * A section's own board below its lanes (plan.md §8.8; L45; B37; C27, C30): the Intake board of questions or the
 * Census board of columns, from `GET review/section/?surface=`. Each takes its rules and asks into the request tray.
 */
export default function SectionBoard({ dealId, surface, meta, readOnly }) {
  const section = useSection(dealId, surface);
  if (section.isPending) return <Loading label="Loading the board…" />;
  if (section.isError) return <InlineError title="The board" error={section.error} onRetry={() => section.refetch()} />;
  const Shown = surface === 'intake' ? IntakeBoard : CensusBoard;
  return <Shown dealId={dealId} board={section.data} meta={meta} readOnly={readOnly} />;
}
