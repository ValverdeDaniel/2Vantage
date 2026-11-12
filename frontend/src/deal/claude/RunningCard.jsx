import { useEffect, useState } from 'react';
import { useStopJob } from '../../api/ai';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { modelLabel, runningTitle, secondsSince, SLOW_NOTE } from './drawerWords';

/*
 * The running card (plan.md §8.17; D21, D22, D27; the old ScanChat's `bb-extract-card`): one job Claude is doing on
 * the deal — what it is, its place in the queue, what it has cost so far, how far it is, the model, its last eight
 * steps (each part of a read names itself: "File 2 of 3: reading pages 1–4"), the seconds since it started with "a
 * big request can take a minute" after 30, and Stop, for every kind (B20): a read keeps what it finished.
 */
function useSeconds(since) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!since) return undefined;
    const handle = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(handle);
  }, [since]);
  return since ? secondsSince(since, now) : 0;
}

export default function RunningCard({ dealId, job, meta }) {
  const toast = useToast();
  const stop = useStopJob(dealId);
  const seconds = useSeconds(job.status === 'running' ? job.started_at : null);
  const steps = (job.recent_steps || []).filter(Boolean);
  const cost = Number(job.cost_usd || 0);
  const model = job.kind === 'read' ? modelLabel(meta, job.model || meta.ai?.default_model) : '';

  async function press() {
    try {
      await stop.mutateAsync(job.id);
      toast.info('Stopping — what Claude finished is kept for review.');
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <div className="bb-extract-card bb-mt" data-running-job={job.id} data-job-status={job.status}>
      <div className="bb-extract-head">
        <div className="bb-extract-title">
          <span className="bb-dot-pulse" /> {runningTitle(job)}
        </div>
        <span className="bnf-extract-right">
          {cost > 0 && (
            <span className="bb-extract-pct bb-mono" title="What this read has cost so far">
              ${cost.toFixed(2)} so far
            </span>
          )}
          <span className="bb-extract-pct bb-mono">{job.progress || 0}%</span>
          <button
            type="button"
            className="btn btn-secondary btn-sm bnf-scan-stop"
            onClick={press}
            disabled={job.stopping || stop.isPending}
            title="Stop this read. What it has read so far is kept for review."
          >
            {job.stopping ? 'Stopping…' : 'Stop'}
          </button>
        </span>
      </div>
      <div className="bb-bar-track bb-bar-track-lg">
        <div className="bb-bar-fill bb-bar-gradient" style={{ width: `${job.progress || 0}%` }} />
      </div>
      {model && job.status === 'running' && (
        <div className="bnf-work-model">
          {model} is reading · {seconds}s
          {seconds >= 30 && <span className="bnf-thinking-note"> — {SLOW_NOTE}</span>}
        </div>
      )}
      {steps.length > 0 && (
        <div className="bb-extract-log bnf-work-steps">
          {steps.map((step, index) => (
            <div key={`${index}-${step}`} className="bb-extract-line">
              <span className="bb-check">{index === steps.length - 1 ? '→' : '✓'}</span> {step}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
