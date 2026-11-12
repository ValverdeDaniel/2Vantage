import { useRef } from "react";
import { useParams } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useAttachSbc as useAttachSbcWrite } from "../../api/ai";
import { documentsKey } from "../../api/documents";
import { useMeta } from "../../api/meta";
import { errorText } from "../../lib/errors";
import { useToast } from "../../ui/useToast";
import { claudeDoor } from "./door";

/*
 * "Attach SBC…" in a plan column's ⋯ menu (plan.md §8.14, §10.4; D38, D47, OQ33; the old ComparisonGrid's
 * `pickSbcFor` / `handleAttachSbc`): one file for one plan, filed on the deal as its SBC and read into that plan's design
 * — never a rate. The read always waits for review, so Work with Claude opens on it and the toast says so. Offered
 * on a medical plan that is not a priced version or a copy (they take their design from their original), and only with
 * Claude set up (D26). `input` is the hidden file picker the menu's item clicks.
 */

export function canAttachSbc(meta, plan) {
  const reads = (meta?.ai?.targets || []).some(
    (target) => target.key === "sbc",
  );
  return reads && plan.line === "medical" && !plan.derived_from;
}

export function useAttachSbc() {
  const { dealId } = useParams();
  const { data: meta } = useMeta();
  const toast = useToast();
  const queryClient = useQueryClient();
  const attach = useAttachSbcWrite(dealId);
  const inputRef = useRef(null);
  const planRef = useRef(null);

  function pick(plan) {
    planRef.current = plan;
    inputRef.current?.click();
  }

  async function onChange(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    const plan = planRef.current;
    if (!file || !plan) return;
    try {
      await attach.mutateAsync({ planId: plan.id, file });
      queryClient.invalidateQueries({ queryKey: documentsKey(dealId) });
      toast.success(
        `Reading the SBC for ${plan.carrier} — ${plan.name}: review it before it changes the plan`,
      );
      claudeDoor.open("sbc");
    } catch (error) {
      toast.error(errorText(error, { fallback: "Could not attach the SBC." }));
    }
  }

  const input = (
    <input
      ref={inputRef}
      type="file"
      accept=".pdf,.png,.jpg,.jpeg"
      hidden
      aria-hidden="true"
      tabIndex={-1}
      onChange={onChange}
    />
  );
  return {
    can: (plan) => canAttachSbc(meta, plan),
    pick,
    input,
    busy: attach.isPending,
  };
}
