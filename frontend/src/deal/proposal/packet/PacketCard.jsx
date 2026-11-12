import { useState } from 'react';
import { useAiState } from '../../../api/ai';
import { useMeta } from '../../../api/meta';
import { useIssue, useRetryIssue } from '../../../api/proposals';
import { templateUrl } from '../../../api/quotes';
import cx from '../../../ui/cx';
import { useToast } from '../../../ui/useToast';
import ChecksList from './ChecksList';
import IssuedList from './IssuedList';
import {
  buildingIssue,
  issueBlocked,
  latestIssued,
  loadPrefs,
  nextVersion,
  savePrefs,
  summaryWords,
  ticked,
} from './packetModel';
import usePacketDoors from './usePacketDoors';

/*
 * The Proposal packet (plan.md §8.15; J96–J104; the old ProposalPacketCard.jsx at 891f1b3, in its BuilderCard look):
 * everything that leaves the building for this deal, in one card over the plan comparison. Its head: ⬇ Download
 * packet (the latest issued version's ticked files in one zip, J96), **Issue to client (v N)** (J103: the `issue` job
 * stamps the option numbers, builds the PDF, PowerPoint and workbook without Draft and keeps them, protected) and Open
 * proposal ▸ (the Export viewer). Its body: the builder's readiness sentence and its Before-you-export checks (J100);
 * the files with their tick and a draft ⬇ Download each (J97, Draft on every page until issued, OQ35); the internal
 * spreadsheet, never in the zip (J98: quotes' plan template, every plan and field); the Issued list (J103). Every
 * door waits for the page's writes (J101). The ticks and the open state are a preference of this browser.
 */
export default function PacketCard({ dealId, proposal, onOpenBuilder, onOpenProposal }) {
  const toast = useToast();
  const { data: meta } = useMeta();
  const [prefs, setPrefs] = useState(loadPrefs);
  const doors = usePacketDoors();
  const issue = useIssue(dealId);
  const retry = useRetryIssue(dealId);
  const ai = useAiState(dealId, {
    onFinished: (job) => {
      if (job.kind !== 'issue') return;
      if (job.status === 'done') toast.success('The proposal is issued: its files are kept as sent.');
      else toast.error(job.error || 'The proposal could not be built. Retry it below.');
    },
  });
  const files = meta?.proposal?.issue?.files ?? [];
  const issues = proposal.issues ?? [];
  const open = Boolean(prefs.open); // closed until opened, as the old card started
  const ticks = prefs.ticks || {};
  const include = ticked(files, ticks);
  const latest = latestIssued(issues);
  const building = buildingIssue(issues);
  const blocked = issueBlocked({ building, saving: doors.saving });
  const jobs = ai.data?.jobs ?? [];

  function remember(patch) {
    const next = { ...prefs, ...patch };
    setPrefs(next);
    savePrefs(next);
  }

  const issueNow = () =>
    doors.deliver(
      'issue',
      async () => {
        const made = await issue.mutateAsync();
        toast.info(`Building proposal v${made.version}: the PDF, the PowerPoint and the spreadsheet.`);
      },
      'Could not issue the proposal',
    );
  const retryNow = (version) =>
    doors.deliver(`v${version}-retry`, () => retry.mutateAsync(version), `Could not retry v${version}`);
  const draft = (file, url = `deals/${dealId}/proposal/files/${file.key}/`) => (
    <button
      type="button"
      className="btn btn-secondary btn-sm"
      aria-busy={doors.busy[file.key] || undefined}
      onClick={() => doors.download(file.key, url, `Could not build the ${file.label}`)}
    >
      {doors.busy[file.key] ? 'Preparing…' : '⬇ Download'}
    </button>
  );

  return (
    <div className={cx('bb-panel bnf-build-panel bnf-bcard bnf-packet-card', !open && 'bnf-bcard-shut')}>
      <div className="bnf-bcard-head">
        <button
          type="button"
          className="bnf-card-toggle bnf-bcard-toggle"
          aria-expanded={open}
          aria-label={open ? 'Collapse Proposal packet' : 'Expand Proposal packet'}
          onClick={() => remember({ open: !open })}
        >
          <span className={cx('bnf-req-chevron', open && 'expanded')} aria-hidden="true">
            ▶
          </span>
          <span className="bb-panel-title bnf-bcard-title">Proposal packet</span>
        </button>
        <span className="bnf-bcard-summary">
          {summaryWords(include.length, files.length, proposal.checks)}
          {building ? ` · v${building.version} building…` : latest ? ` · v${latest.version} issued` : ''}
        </span>
        <span className="bnf-bcard-mark">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!latest || !include.length}
            aria-busy={doors.busy.packet || undefined}
            title={
              !latest
                ? 'Issue the proposal first: the packet holds an issued version’s files'
                : include.length
                  ? `Proposal v${latest.version}: the ticked files, in one zip`
                  : 'Open the card and tick at least one file'
            }
            onClick={() =>
              doors.download('packet', `deals/${dealId}/proposal/issues/${latest.version}/packet/`, 'Could not build the packet', {
                include: include.join(','),
              })
            }
          >
            {doors.busy.packet ? 'Preparing…' : '⬇ Download packet'}
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={Boolean(blocked) || doors.busy.issue}
            title={blocked || 'Stamps the option numbers and keeps the PDF, the PowerPoint and the spreadsheet as sent'}
            onClick={issueNow}
          >
            {doors.busy.issue ? 'Issuing…' : `Issue to client (v${nextVersion(issues)})`}
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onOpenProposal}>
            Open proposal ▸
          </button>
        </span>
      </div>
      {open && (
        <>
          <div className="bnf-packet-note">
            Follows the proposal builder: what you pick there is what prints here.{' '}
            <button type="button" className="bnf-override-link" onClick={onOpenBuilder}>
              Open proposal builder ▸
            </button>
          </div>
          {proposal.ready?.sentence && (
            <div className="bnf-build-ready" role="status">
              {proposal.ready.sentence}
            </div>
          )}
          <ChecksList checks={proposal.checks} />
          <div className="bnf-packet-group">In the zip</div>
          {files.map((file) => (
            <div className="bnf-packet-row" key={file.key}>
              <label className="bnf-packet-tick">
                <input
                  type="checkbox"
                  checked={ticks[file.key] !== false}
                  onChange={(event) => remember({ ticks: { ...ticks, [file.key]: event.target.checked } })}
                />
                <span className="bnf-packet-label">{file.label}</span>
              </label>
              <span className="bnf-packet-hint">{file.hint} · draft</span>
              {draft(file)}
            </div>
          ))}
          <div className="bnf-packet-group">Separate downloads, never in the zip</div>
          <div className="bnf-packet-row">
            <span className="bnf-packet-tick bnf-packet-label">Internal spreadsheet</span>
            <span className="bnf-packet-hint bnf-packet-hint-warn">
              Internal — not for clients: every plan, stop-loss lasers too
            </span>
            {draft({ key: 'internal', label: 'internal spreadsheet' }, templateUrl(dealId))}
          </div>
          <IssuedList
            dealId={dealId}
            issues={issues}
            files={files}
            include={include}
            jobs={jobs}
            doors={doors}
            onRetry={retryNow}
          />
        </>
      )}
    </div>
  );
}
