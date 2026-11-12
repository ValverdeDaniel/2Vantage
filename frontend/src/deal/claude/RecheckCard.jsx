import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useApplyRead, useDiscardRead, useJob } from "../../api/ai";
import { errorText } from "../../lib/errors";
import Loading from "../../ui/Loading";
import { useToast } from "../../ui/useToast";
import { flashWhenSettled } from "./flashPlans";
import {
  firstPicks,
  recheckSource,
  recheckTitle,
  rowMeta,
  sections,
} from "./recheckWords";

/*
 * Claude's re-check of the flagged values, waiting for a person (plan.md §10.4, §10.7; D93, E77, D-119; the old
 * ProposedChangesCard's flag re-check, `bnf-pchg-*`): what Claude agrees with, ticked, to approve; what it would fix,
 * old → new; and what it could not find on its page, still flagged. Nothing changes until "Apply N selected ▸": the
 * approvals then carry the person who pressed it (`via: recheck`) and ↶ Undo this run takes them back. Discard drops it.
 */
const RESOLVED = new Set(["applied", "discarded", "undone"]);

function Row({ item, picked, busy, onToggle, onOpen }) {
  const value = item.values[0];
  const agree = item.op === "confirm";
  return (
    <label
      className={`bnf-pchg-row${item.stale ? " is-stale" : ""}`}
      title={value.note ? `Claude: “${value.note}”` : ""}
    >
      <input
        type="checkbox"
        checked={picked}
        disabled={busy || item.frozen}
        onChange={() => onToggle(item.id)}
      />
      <span className="bnf-pchg-field">{value.label}</span>
      {agree ? (
        <span className="bnf-pchg-values">
          <span className="bnf-pchg-agree">✓ {value.old || "—"}</span>{" "}
          <span className="bnf-pchg-agree-note">right as read</span>
        </span>
      ) : (
        <span className="bnf-pchg-values">
          <span className="bnf-pchg-old">{value.old || "—"}</span>
          {" → "}
          <span className="bnf-pchg-new">{value.new || "—"}</span>
        </span>
      )}
      <span className="bnf-pchg-meta">
        {value.doc && value.page && onOpen ? (
          <button
            type="button"
            className="bnf-linklike"
            title="Open the file at this page"
            onClick={(event) => {
              event.preventDefault();
              onOpen(value.doc, value.page);
            }}
          >
            p.{value.page} ↗
          </button>
        ) : null}{" "}
        {rowMeta({
          ...value,
          page: value.doc && value.page && onOpen ? null : value.page,
        })}
        {item.why ? ` · ${item.why}` : ""}
      </span>
    </label>
  );
}

export default function RecheckCard({ dealId, jobId, nameOf, onOpen }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const job = useJob(jobId);
  const apply = useApplyRead(dealId);
  const discard = useDiscardRead(dealId);
  const [picked, setPicked] = useState(null);
  const changeSet = job.data?.result;
  if (job.isPending) return <Loading label="Loading the re-check…" />;
  if (!changeSet?.items || RESOLVED.has(job.data?.resolution)) return null;
  const chosen = picked ?? firstPicks(changeSet);
  const pickable = changeSet.items.filter((item) => !item.frozen);
  const allPicked =
    pickable.length > 0 && pickable.every((item) => chosen.has(item.id));
  const busy = apply.isPending || discard.isPending;
  const unverified = changeSet.unverified || [];

  const toggle = (id) => {
    const next = new Set(chosen);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setPicked(next);
  };

  async function use() {
    try {
      const { landed } = await apply.mutateAsync({
        jobId,
        select: [...chosen],
      });
      toast.success(
        `Applied — ${landed.summary}. ↶ Undo this run takes it back.`,
      );
      flashWhenSettled(queryClient, dealId, landed.plan_ids);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  async function drop() {
    try {
      await discard.mutateAsync(jobId);
      toast.success("Discarded — nothing changed.");
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <div className="bnf-pchg bb-mt" data-recheck-job={jobId}>
      <div className="bnf-pchg-head">
        <div>
          <div className="bnf-pchg-title">{recheckTitle(changeSet)}</div>
          <div className="bnf-pchg-sub">
            {recheckSource(changeSet, nameOf)}. Nothing has changed yet — untick
            anything wrong, then apply.
          </div>
        </div>
      </div>
      <label className="bnf-pchg-all">
        <input
          type="checkbox"
          checked={allPicked}
          disabled={busy}
          onChange={() =>
            setPicked(
              allPicked ? new Set() : new Set(pickable.map((item) => item.id)),
            )
          }
        />{" "}
        All {pickable.length}
      </label>
      <div className="bnf-pchg-list">
        {sections(changeSet).map((section) => (
          <div key={section.key}>
            <div className={`bnf-pchg-section bnf-pchg-section-${section.key}`}>
              <div className="bnf-pchg-section-title">{section.title}</div>
              <div className="bnf-pchg-section-note">{section.note}</div>
            </div>
            {section.groups.map((group) => (
              <div
                key={`${section.key}-${group.plan}`}
                className="bnf-pchg-plan"
              >
                <div className="bnf-pchg-plan-name">{group.label}</div>
                {group.items.map((item) => (
                  <Row
                    key={item.id}
                    item={item}
                    picked={chosen.has(item.id)}
                    busy={busy}
                    onToggle={toggle}
                    onOpen={onOpen}
                  />
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>
      {unverified.length > 0 && (
        <div className="bnf-pchg-note bnf-pchg-unverified">
          <b>Couldn’t find on its page ({unverified.length})</b> — still
          flagged, nothing to apply; check{" "}
          {unverified.length === 1 ? "it" : "them"} by hand:{" "}
          {unverified
            .slice(0, 6)
            .map(
              (row) =>
                `${row.plan_label} · ${row.label} ${row.value || "—"}${row.page ? ` (p.${row.page})` : ""}`,
            )
            .join("; ")}
          {unverified.length > 6 ? "…" : ""}
        </div>
      )}
      {(changeSet.findings || []).map((finding) => (
        <div key={finding.text} className="bnf-pchg-note">
          {finding.text}
        </div>
      ))}
      <div className="bnf-pchg-actions">
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
          disabled={busy || chosen.size === 0}
          onClick={use}
        >
          {apply.isPending ? "Applying…" : `Apply ${chosen.size} selected ▸`}
        </button>
      </div>
    </div>
  );
}
