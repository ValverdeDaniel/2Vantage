import { useState } from 'react';
import { Link } from 'react-router';
import { useApplyRead, useDiscardRead, useJob } from '../../api/ai';
import { useStagedReads } from '../../api/questionnaire';
import { errorText } from '../../lib/errors';
import Loading from '../../ui/Loading';
import { useToast } from '../../ui/useToast';
import { claudeDoor } from './door';
import { applyBody, initialPicks, pickKey, readSections, signedNote, togglePick } from './formReads';
import { failedText, landedToast, leftOutText, summaryLine } from './readWords';

/*
 * "Review this scan" for a filled form Claude read (plan.md §10.5, §8.17; D28, D31, D74, G99, G100, G108; slice 52).
 * The job's change set only points at the staged read, so the card reads it from the questionnaire's own door,
 * worked out against the form as it stands: the answers (the old IntakeDiff's Question · New scan · Current table,
 * each with its tick, ↗ to its page, and why one arrives unticked), the rows and where each goes (a new row, or the
 * form's row N), then what is left alone — answers a person stands behind, never written over. "Use this scan ▸" uses
 * the read as proposed; once a tick changes, "Apply N selected ▸" uses exactly what is ticked. A signed form takes
 * nothing: the button stays off and the card says to reopen the form (G99). Discard drops it (D74). A sensitive
 * answer shows here as on the form, and nowhere else.
 */
const RESOLVED = new Set(['applied', 'discarded', 'undone']);

function Tick({ entry, form, picked, onToggle }) {
  const key = pickKey(form, entry.ref);
  return (
    <input type="checkbox" aria-label={`Use ${entry.label}`} checked={picked.has(key)} onChange={() => onToggle(key)} />
  );
}

function FormRead({ dealId, read, picked, onToggle, onOpen, document }) {
  const { answers, rows, conflicts } = readSections(read);
  const pin = (entry) =>
    entry.page && onOpen ? (
      <button
        type="button"
        className="bnf-src-pin"
        title={`See it on page ${entry.page} of the file`}
        onClick={() => onOpen(document, entry.page)}
      >
        ↗
      </button>
    ) : null;
  return (
    <div className="bnf-staged-section" data-questionnaire-read={read.id}>
      <div className="bnf-staged-section-title">
        {read.label}{' '}
        <Link
          className="bnf-linklike"
          to={`/deals/${dealId}/questionnaire?form=${read.form}`}
          onClick={() => claudeDoor.close()}
        >
          Open on the Questionnaire tab ▸
        </Link>
      </div>
      {answers.length > 0 && (
        <div className="bb-grid-card bb-mt">
          <table className="bnf-compare-table">
            <thead>
              <tr>
                <th aria-label="Use" />
                <th className="bnf-benefit-col">Question</th>
                <th>New scan</th>
                <th>Current</th>
              </tr>
            </thead>
            <tbody>
              {answers.map((entry) => (
                <tr key={entry.ref} data-entry={entry.ref}>
                  <td>
                    <Tick entry={entry} form={read.form} picked={picked} onToggle={onToggle} />
                  </td>
                  <td className="bnf-benefit-col">
                    {entry.label}
                    {entry.why ? <div className="bnf-staged-scope-note">{entry.why}</div> : null}
                  </td>
                  <td className="bnf-cell bnf-staged-changed" title={entry.low || undefined}>
                    {entry.shown}
                    {pin(entry)}
                  </td>
                  <td className="bnf-cell bb-empty">{entry.was}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {rows.length > 0 && (
        <ul className="bnf-staged-list">
          {rows.map((entry) => (
            <li key={entry.ref} data-entry={entry.ref}>
              <Tick entry={entry} form={read.form} picked={picked} onToggle={onToggle} /> <strong>{entry.where}</strong>
              {pin(entry)}: {entry.text}
              {entry.why ? <div className="bnf-staged-scope-note">{entry.why}</div> : null}
            </li>
          ))}
        </ul>
      )}
      {conflicts.length > 0 && (
        <>
          <div className="bnf-staged-section-title">Left alone</div>
          <ul className="bnf-staged-list">
            {conflicts.map((entry) => (
              <li key={entry.ref} data-entry={entry.ref}>
                {entry.label}: the file says {entry.shown}, the form {entry.was}. {entry.why}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default function QuestionnaireReadCard({ dealId, jobId, meta, nameOf, onOpen }) {
  const toast = useToast();
  const job = useJob(jobId);
  const discard = useDiscardRead(dealId);
  const apply = useApplyRead(dealId);
  const [picks, setPicks] = useState(null);
  const changeSet = job.data?.result;
  const items = changeSet?.items || [];
  const queries = useStagedReads(dealId, items.map((item) => item.read));
  if (job.isPending || queries.some((query) => query.isPending)) return <Loading label="Loading the read…" />;
  if (!items.length || RESOLVED.has(job.data?.resolution)) return null;
  const reads = queries.map((query) => query.data).filter((read) => read?.status === 'waiting');
  if (!reads.length) return null;
  const initial = initialPicks(reads);
  const picked = picks ?? initial;
  const body = applyBody(picked, initial);
  const proposed = !body.select;
  const blocked = signedNote(reads);
  const busy = discard.isPending || apply.isPending;
  const words = meta.ai || {};
  const notes = [
    changeSet.partial && !changeSet.failed_parts?.length ? 'Stopped before the end: this is what was read.' : '',
    changeSet.halted || '',
    failedText(changeSet.failed_parts, nameOf, words.failed_words),
    leftOutText(changeSet.left_out_pages, nameOf, words.left_out_words),
    blocked,
  ].filter(Boolean);

  async function drop() {
    try {
      await discard.mutateAsync(jobId);
      toast.success('Read discarded. Nothing on the form changed.');
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  async function use() {
    try {
      const { landed } = await apply.mutateAsync({ jobId, ...body });
      toast.success(landedToast(landed));
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <div className="bnf-staged-review bb-mt" data-review-job={jobId} data-questionnaire-job={jobId}>
      <div className="bnf-staged-head">
        <div>
          <div className="bb-panel-title">Review this scan</div>
          <div className="bb-panel-sub">
            Nothing has changed yet. Compare the filled form against the questionnaire, then keep whichever you want.
            An answer a person typed, approved or the client gave is never written over.
          </div>
        </div>
        <div className="bnf-staged-actions">
          <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={drop}>
            Discard
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={busy || Boolean(blocked) || (!proposed && !picked.size)}
            onClick={use}
            title={
              blocked ||
              (proposed
                ? 'Use the read as Claude proposes it: the ticked answers and rows. What Claude was unsure of stays out until you tick it.'
                : 'Use only what is ticked here.')
            }
          >
            {apply.isPending ? 'Applying…' : proposed ? 'Use this scan ▸' : `Apply ${picked.size} selected ▸`}
          </button>
        </div>
      </div>
      <div className="bnf-staged-summary">{summaryLine(changeSet, words.models)}</div>
      {notes.map((note) => (
        <div key={note} className="bnf-staged-scope-note">
          {note}
        </div>
      ))}
      {reads.map((read) => (
        <FormRead
          key={read.id}
          dealId={dealId}
          read={read}
          picked={picked}
          onToggle={(key) => setPicks(togglePick(picked, key))}
          onOpen={onOpen}
          document={read.document}
        />
      ))}
      {changeSet.findings?.length > 0 && (
        <div className="bnf-staged-section">
          <div className="bnf-staged-section-title">Worth a look</div>
          <ul className="bnf-staged-list">
            {changeSet.findings.map((finding) => (
              <li key={finding.text}>{finding.text}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
