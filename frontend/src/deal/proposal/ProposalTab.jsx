import { useState } from 'react';
import { useProposal, useSaveProposal } from '../../api/proposals';
import { useSetRecommended } from '../../api/quotes';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import EmptyState from '../../ui/EmptyState';
import Field from '../../ui/Field';
import InlineError from '../../ui/InlineError';
import SaveStatus from '../../ui/SaveStatus';
import Skeleton from '../../ui/Skeleton';
import TextInput from '../../ui/TextInput';
import { useToast } from '../../ui/useToast';
import ProposalLine from './ProposalLine';
import styles from './ProposalTab.module.css';

function SavedText({ label, value, onSave, multiline }) {
  const [draft, setDraft] = useState(null);
  return (
    <Field label={label}>
      <TextInput
        multiline={multiline}
        rows={multiline ? 2 : undefined}
        value={draft ?? value}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => {
          if (draft !== null && draft !== value) onSave(draft);
          setDraft(null);
        }}
      />
    </Field>
  );
}

/**
 * The Proposal tab (plan.md §8.12): what each line presents, the firm's recommendation and why, and a preview of
 * exactly what the client workbook will print. The workbook itself (M7) and issuing it (M8) come next.
 */
export default function ProposalTab({ deal }) {
  const toast = useToast();
  const proposal = useProposal(deal.id);
  const save = useSaveProposal(deal.id);
  const recommend = useSetRecommended(deal.id);

  if (proposal.isPending) return <Skeleton lines={8} height="18px" label="Loading the proposal…" />;
  if (proposal.isError) return <InlineError error={proposal.error} onRetry={() => proposal.refetch()} />;
  const data = proposal.data;
  const saveField = (changes) => save.mutateAsync(changes).catch((error) => toast.error(errorText(error)));

  return (
    <div className={styles.tab}>
      <div className={styles.top}>
        <div className={styles.meta}>
          <SavedText label="Title" value={data.title} onSave={(title) => saveField({ title })} />
          <SavedText label="Notes" value={data.notes} multiline onSave={(notes) => saveField({ notes })} />
          <SaveStatus mutation={save} />
        </div>
        <aside className={styles.issue} aria-label="Issue to client">
          {data.issue_blockers.length ? (
            <>
              <p className={styles.blocker}>Not ready to issue:</p>
              <ul>
                {data.issue_blockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            </>
          ) : (
            data.lines.length > 0 && <p>Every current plan has a recommendation.</p>
          )}
          <Button variant="primary" disabled title="The client workbook (M7) and issuing (M8) come next">
            Issue to client
          </Button>
          <p className={styles.muted}>The client workbook and issuing arrive in the next slices (M7–M8).</p>
        </aside>
      </div>

      {!data.lines.length && (
        <EmptyState title="Nothing to present yet">
          Add plans to the deal&apos;s lines in the Advisor; each requested line with plans appears here.
        </EmptyState>
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
  );
}
