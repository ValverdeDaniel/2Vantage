import { useAiState, useStartRecheck } from "../../api/ai";
import { useMeta } from "../../api/meta";
import { errorText } from "../../lib/errors";
import { useToast } from "../../ui/useToast";
import { claudeDoor } from "./door";

/*
 * ✦ Ask Claude to re-check (plan.md §10.4, §10.7; D40, D93, E77, F66; slice 22; the old CaseWorkspace's
 * `recheckFlags`): the flagged values a strip names — some plans, the files on screen, or every flag on the deal — read
 * again against their pages in a job of their own. Work with Claude opens on it; its card waits there (and under its
 * file on Documents) until a person applies it. `null` without Claude set up (D26), so the strips draw no button.
 * `suggest`: past how many open warnings the strip says a second read often settles them (the server's, E80).
 */
export default function useRecheck(dealId) {
  const { data: meta } = useMeta();
  const toast = useToast();
  const start = useStartRecheck(dealId);
  const ai = useAiState(dealId);
  if (!meta?.ai || !ai.data?.claude) return null;

  async function run(scope) {
    try {
      await start.mutateAsync(scope);
      toast.success(
        "Claude is re-checking the flagged values against their pages. Nothing changes until you apply it.",
      );
      claudeDoor.open();
    } catch (error) {
      toast.error(
        errorText(error, { fallback: "Could not start the re-check." }),
      );
    }
  }

  return { run, busy: start.isPending, suggest: ai.data.flags?.suggest };
}
