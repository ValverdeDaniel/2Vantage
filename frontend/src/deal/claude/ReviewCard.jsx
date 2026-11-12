import { Suspense, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useApplyRead, useDiscardRead, useJob } from "../../api/ai";
import { errorText } from "../../lib/errors";
import Loading from "../../ui/Loading";
import { useToast } from "../../ui/useToast";
import {
  applyBody,
  asProposed,
  initialPicks,
  pickedCount,
  togglePick,
} from "../advisor/claude/changeSet";
import { flashWhenSettled } from "./flashPlans";
import { failedText, landedToast, leftOutText, summaryLine } from "./readWords";

/*
 * "Review this scan" (plan.md §10.5; D28, D31, D72, D74, E78; the old StagedScanReview and ProposedChangesCard): one
 * read's change set, waiting for a person. The head says nothing has changed yet; notes name a stopped or partial
 * read, its failed parts and the pages it did not read; the reader's own body (`renderer`, e.g. the quote reader's
 * plans) shows what would change, each item and each unticked value with its tick, and ↗ to see a value in its file
 * (`onOpen`); then what the read found worth a look.
 * - "Use this scan ▸" uses the read as Claude proposes it; once the person changes a tick the same button says "Apply
 *   N selected ▸" and uses exactly what is ticked (the printed counts, a value left alone, where a current plan goes).
 *   Both land through the owner's services, one transaction, with ↶ Undo this run after (D73); the plans it changed
 *   flash on the table behind (D35).
 * - Discard drops it (D74).
 */
const RESOLVED = new Set(["applied", "discarded", "undone"]); // a stopped read still waits, with what it read

export default function ReviewCard({
  dealId,
  jobId,
  renderer: Body,
  meta,
  nameOf,
  onOpen,
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const job = useJob(jobId);
  const discard = useDiscardRead(dealId);
  const apply = useApplyRead(dealId);
  const [picks, setPicks] = useState(null);
  const [places, setPlaces] = useState({});
  const changeSet = job.data?.result;
  if (job.isPending) return <Loading label="Loading the read…" />;
  if (!changeSet?.items || RESOLVED.has(job.data?.resolution)) return null;
  const picked = picks ?? initialPicks(changeSet);
  const toggle = (id, itemId = null) =>
    setPicks(togglePick(picked, id, itemId));
  const place = (itemId, where) => setPlaces({ ...places, [itemId]: where });
  const proposed = asProposed(picked, changeSet);
  const count = pickedCount(picked, changeSet);
  const busy = discard.isPending || apply.isPending;
  const words = meta.ai || {};
  const notes = [
    changeSet.partial && !changeSet.failed_parts?.length
      ? "Stopped before the end: this is what was read."
      : "",
    changeSet.halted || "",
    failedText(changeSet.failed_parts, nameOf, words.failed_words),
    leftOutText(changeSet.left_out_pages, nameOf, words.left_out_words),
  ].filter(Boolean);

  async function drop() {
    try {
      await discard.mutateAsync(jobId);
      toast.success("Read discarded. Nothing on the deal changed.");
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  async function use() {
    try {
      const { landed } = await apply.mutateAsync({
        jobId,
        ...applyBody(picked, changeSet, places),
      });
      toast.success(landedToast(landed));
      flashWhenSettled(queryClient, dealId, landed.plan_ids);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  // The reader's body loads with its tab's code (renderers.js): the whole card waits for it, so it shows complete.
  return (
    <Suspense fallback={<Loading label="Loading the read…" />}>
      <div className="bnf-staged-review bb-mt" data-review-job={jobId}>
        <div className="bnf-staged-head">
          <div>
            <div className="bb-panel-title">Review this scan</div>
            <div className="bb-panel-sub">
              Nothing has changed yet. Compare the new read against what&apos;s
              on the deal, then keep whichever you want. Using this scan never
              deletes a plan.
            </div>
          </div>
          <div className="bnf-staged-actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={busy}
              onClick={drop}
            >
              Discard
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy || (!proposed && !count)}
              onClick={use}
              title={
                proposed
                  ? "Use the read as Claude proposes it: the ticked plans and values. Printed counts and anything unsure stay out until you tick them."
                  : "Use only what is ticked here."
              }
            >
              {apply.isPending
                ? "Applying…"
                : proposed
                  ? "Use this scan ▸"
                  : `Apply ${count} selected ▸`}
            </button>
          </div>
        </div>
        <div className="bnf-staged-summary">
          {summaryLine(changeSet, words.models)}
        </div>
        {notes.map((note) => (
          <div key={note} className="bnf-staged-scope-note">
            {note}
          </div>
        ))}
        {Body ? (
          <Body
            changeSet={changeSet}
            meta={meta}
            picked={picked}
            onToggle={toggle}
            places={places}
            onPlace={place}
            onOpen={onOpen}
          />
        ) : null}
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
    </Suspense>
  );
}
