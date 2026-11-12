import { issuedFileUrl } from '../../../api/proposals';
import cx from '../../../ui/cx';
import { issueWords } from './packetModel';

/*
 * The Issued list on the packet card (plan.md §8.15; J103, J96, J114): every version, newest first. An issued one
 * downloads its stored files as the client was sent them (never rebuilt), its Letter PDF (made from the stored PDF)
 * and its packet (the ticked files in one zip); one still building shows the job's progress from the deal's AI poll;
 * a failed one says why, with Retry, which builds the same version again.
 */
export default function IssuedList({ dealId, issues, files, include, jobs, doors, onRetry }) {
  if (!issues.length) return null;
  return (
    <>
      <div className="bnf-packet-group">Issued to the client</div>
      {issues.map((issue) => {
        const live = jobs.find((job) => job.id === issue.job?.id);
        const url = (file) => issuedFileUrl(dealId, issue.version, file);
        const key = (file) => `v${issue.version}-${file}`;
        const button = (file, label, params) => (
          <button
            key={file}
            type="button"
            className="btn btn-secondary btn-sm"
            aria-busy={doors.busy[key(file)] || undefined}
            onClick={() => doors.download(key(file), url(file), `Could not download v${issue.version}`, params)}
          >
            {doors.busy[key(file)] ? 'Preparing…' : `⬇ ${label}`}
          </button>
        );
        return (
          <div className="bnf-packet-row" key={issue.version} data-issue={issue.state}>
            <span className="bnf-packet-tick bnf-packet-label">Proposal v{issue.version}</span>
            <span className={cx('bnf-packet-hint', issue.state === 'failed' && 'bnf-packet-hint-warn')}>
              {issue.state === 'building' && <span className="bb-dot-pulse" aria-hidden="true" />} {issueWords(issue, live)}
            </span>
            {issue.state === 'issued' && (
              <>
                {files.map((file) => button(file.key, file.label))}
                {button('letter', 'Letter PDF')}
                {button('packet', 'Packet', { include: include.join(',') })}
              </>
            )}
            {issue.state === 'failed' && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                aria-busy={doors.busy[key('retry')] || undefined}
                onClick={() => onRetry(issue.version)}
              >
                ↻ Retry
              </button>
            )}
          </div>
        );
      })}
    </>
  );
}
