import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router';
import { useAiState, useStartRecheck } from '../../../api/ai';
import { confidenceKey } from '../../../api/confidence';
import { useMeta } from '../../../api/meta';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import { claudeDoor } from '../../claude';
import { recheckBlocked, recheckResult } from './confidenceWords';

const RESOLVED = { applied: 'applied', discarded: 'discarded', undone: 'undone' };

/**
 * The AI re-read (plan.md §8.6, §10.4; M92, M93; D-119; old Vantage 891f1b3 `DataConfidence.jsx`'s audit panel): Double-
 * check with AI starts `ai`'s one `recheck` reader on the deal's scanned values — every value read from a file that no
 * person approved, open warnings first — in the work lane. It is off without Claude, with nothing scanned, while any
 * read runs, and while it runs itself (the AI state's jobs). Its last result reads "Re-read N scanned values — N
 * agreed · N disagree · N not found" with the first six differences and Open the documents ▸; nothing on the deal
 * changes until a person applies its card, which waits in Work with Claude (Review ▸).
 */
export default function RecheckPanel({ dealId, recheck }) {
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries({ queryKey: confidenceKey(dealId) });
  const ai = useAiState(dealId, { onFinished: refresh });
  const start = useStartRecheck(dealId);
  const meta = useMeta().data;
  const toast = useToast();
  const jobs = ai.data?.jobs || [];
  const rechecking = start.isPending || jobs.some((job) => job.kind === 'recheck');
  const busy = jobs.some((job) => job.lane === 'work');
  const blocked = recheckBlocked({ claude: Boolean(meta?.ai && ai.data?.claude), values: recheck.values, running: busy });
  const { last } = recheck;
  const result = recheckResult(last);

  async function run() {
    try {
      await start.mutateAsync({ scanned: true });
      toast.success('Claude is re-reading the scanned values against their files. Nothing changes until you apply it.');
      refresh();
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not start the re-read.' }));
    }
  }

  return (
    <div className="bnf-ov-audit">
      <div className="bnf-ov-audit-head">
        <span className="bnf-ov-audit-title">AI re-read</span>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={rechecking || !!blocked}
          title={blocked || 'Claude re-opens each source file and checks the values we hold against it'}
          onClick={run}
        >
          {rechecking ? 'Re-reading…' : 'Double-check with AI'}
        </button>
      </div>
      {blocked && !rechecking && <div className="bb-drop-meta">{blocked}</div>}
      {result && (
        <>
          <div className="bnf-ov-audit-result">
            {result.head}
            <span className="bb-green">{result.agreed}</span>
            {result.differ && (
              <>
                {' · '}
                <span className="bb-rose">{result.differ}</span>
              </>
            )}
            {result.notFound && (
              <>
                {' · '}
                <span className="bb-amber">{result.notFound}</span>
              </>
            )}
            {result.at && <span className="bb-drop-meta"> · {result.at}</span>}
            {RESOLVED[last.resolution] && <span className="bb-drop-meta"> · {RESOLVED[last.resolution]}</span>}
          </div>
          {last.waiting && (
            <div className="bb-drop-meta">
              Waiting for you — nothing changes until you apply it.{' '}
              <button type="button" className="bnf-override-link" onClick={() => claudeDoor.open()}>
                Review ▸
              </button>
            </div>
          )}
          {last.differences.length > 0 && (
            <div className="bnf-ov-audit-rows">
              {last.differences.map((row, index) => (
                <div key={`${row.label}:${index}`} className="bnf-ov-audit-row">
                  <span className="bnf-ov-audit-label">{row.label}</span>
                  <span className="bnf-ov-audit-diff">
                    <span className="bb-mono">{row.old}</span>
                    <span className="bnf-ov-audit-arrow">→</span>
                    <span className="bb-mono bb-rose">{row.new || '—'}</span>
                  </span>
                  <span className="bb-drop-meta">
                    {row.doc?.name}
                    {row.page ? ` p.${row.page}` : ''}
                  </span>
                </div>
              ))}
              <Link className="bnf-override-link" to={`/deals/${dealId}/documents`}>
                Open the documents to check these ▸
              </Link>
            </div>
          )}
        </>
      )}
      {last?.status === 'failed' && <div className="bb-drop-meta bb-rose">{last.error || 'The re-read failed.'}</div>}
      {!last && !blocked && (
        <div className="bb-drop-meta">
          Not run yet — the AI will re-open each source document and check the values we hold against it.
        </div>
      )}
    </div>
  );
}
