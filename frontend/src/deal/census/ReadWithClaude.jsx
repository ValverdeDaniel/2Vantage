import { useStartRead } from '../../api/ai';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import { useToast } from '../../ui/useToast';
import { claudeDoor } from '../claude';
import { censusReader } from './claudeCensus';

/*
 * "Not our template? Read it with Claude ▸" (plan.md §8.17, §10.4; D42, D109; slice 51): the mapping dialog hands a
 * census spreadsheet the usual mapping could not place to Claude's census reader. Claude is shown the columns' headers
 * and the shapes of their values, never a value (D109), and proposes the columns left; the file comes back to this
 * dialog with them marked Check, the person's own choices kept. Work with Claude opens to show the read going. Shown
 * only while the census reader is there (with Claude and the PHI-gate switch on).
 */
export default function ReadWithClaude({ dealId, imp, meta, disabled, onStarted }) {
  const toast = useToast();
  const start = useStartRead(dealId);
  if (censusReader(meta).state !== 'on' || !imp.document_id) return null;

  async function read() {
    try {
      await start.mutateAsync({ documentIds: [imp.document_id], target: 'census' });
      toast.success('Claude is mapping the columns from their shapes. The file comes back here when it is done.');
      claudeDoor.open('census');
      onStarted?.();
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <Button
      size="sm"
      busy={start.isPending}
      disabled={disabled}
      onClick={read}
      title="Claude sees the column headers and the shapes of their values (9 digits, a date, 2 letters), never a value."
    >
      Not our template? Read it with Claude ▸
    </Button>
  );
}
