import cx from '../../ui/cx';
import { finishedWords, runningWords } from './checkWords';

/*
 * What "Check this file" is doing, and what it found (plan.md §8.16; E59, D21, D22): the old app's Claude strip
 * (`bnf-claude-strip`, CaseWorkspace's ClaudeStrip) over the file. While the job runs: the pulse, "· 40% — Reading
 * page 120 of 1,500" and Stop. When it ends: "✓ Checked 12 values against the file — 2 not found in it", "Stopped",
 * or why it failed, until dismissed.
 */
export default function CheckStrip({ check, count }) {
  const { job, ended, stopping } = check;
  if (job) {
    const { text, line } = runningWords(job, count);
    return (
      <div className="bnf-claude-strip" role="status" data-check-job={job.id} data-check-status={job.status}>
        <span className="bb-dot-pulse" aria-hidden="true" />
        <span className="bnf-claude-strip-text">
          {text}
          {line ? <span className="bnf-claude-strip-line"> — {line}</span> : null}
        </span>
        <button type="button" className="btn btn-secondary btn-sm" disabled={stopping} onClick={check.stop}>
          {stopping ? 'Stopping…' : 'Stop'}
        </button>
      </div>
    );
  }
  if (!ended) return null;
  const { tone, text } = finishedWords(ended, count);
  return (
    <div
      className={cx(
        'bnf-claude-strip',
        tone === 'landed' && 'bnf-claude-strip-landed',
        tone !== 'landed' && 'bnf-claude-strip-news',
        tone === 'failed' && 'bnf-claude-strip-failed',
      )}
      role="status"
      data-check-job={ended.id}
      data-check-status={ended.status}
    >
      <span className="bnf-claude-strip-text">
        {tone === 'landed' ? '✓ ' : ''}
        {text}
      </span>
      <button type="button" className="bnf-claude-strip-x" onClick={check.dismiss} aria-label="Dismiss">
        ✕
      </button>
    </div>
  );
}
