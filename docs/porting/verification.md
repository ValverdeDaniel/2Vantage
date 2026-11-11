# Verification

[← Porting plan](README.md)

## V.1 How each slice is verified
A slice is done when all of these hold (plan.md §13's "done when", extended):
1. Its Needs are committed, and the old-repo commit it ports from is named (P.1).
2. Each item it builds has behavioural tests named with its ID (for example `test_F45_pick_replaces_slot`).
3. The golden deals are extended; a key changes only with Stephanie's agreement.
4. The Fast, Front and Lint lanes are green and within budget.
5. The Q.3 contracts cover every new service and endpoint: a permission row, sample GET arguments and a scaling test.
6. If it touches PHI, Activity or AI context, the canaries pass.
7. If it touches a painter, Recalc and Fidelity run on the affected golden deals with no unexplained difference.
8. If it touches screens, Look runs on them with no unlabelled difference.
9. If it touches a reader, the recorded tests pass; if the model, prompt, schema or merge rules changed, Eval meets its thresholds.
10. The "done when" is walked in the browser on a golden deal, scripted when the slice advances one of the twelve needs.
11. Daniel's summary lists the item IDs built, the needs advanced, the intended differences added, and the lanes run with their results. The change is left uncommitted.

## V.2 MVP acceptance
**When.** Milestone 1 (after slice 37) runs Gates A and B on slices 1–37, then Gate C on plan data and typed counts. Milestone 2 (after slice 66) runs all three again on the full MVP, because later slices change shared code. The MVP is accepted only at Milestone 2.

**Gate A: automated,** on a fresh database with the production image:
- every lane green;
- Fidelity for the four client outputs on the parity profiles of GD1, GD2, GD3 and GD5, and for the secondary outputs on GD6;
- every MVP screen labelled in Look;
- Eval at its thresholds with the chosen default model;
- the release gate: `check --deploy` and `/api/health/`; at Milestone 2, also the staging canary scan.

**Gate B: Daniel walks the twelve needs on staging.**

| Need | Deal | Passes when |
|---|---|---|
| 1 Scan quotes | GD3 | The dropped packet and quote become plans in printed order, with renewals linked. A direct person's read lands at once; a producer's is reviewed, then applied. Undo restores |
| 2 SBCs and quotes | GD3 | Attach SBC fills design values only and flags disagreements. Values are checked and approved beside the highlighted file (scanned pages from slice 65). A re-check is staged until a person applies it |
| 3 Order and rows | GD3 | "As quoted" and Documents repeat the file's columns and rows, unmatched rows included |
| 4 Search | GD1 | Words, plan numbers and aliases find the key's plans; the other-line chip switches lines |
| 5 Budget | GD1 | A cap on the monthly total leaves the key's plans and names the plans with no total |
| 6 Enrollment | GD3 A/B, GD4 | Typed counts price every plan; a second current plan asks for the split and prices after it; the census takes over after its import, with the notice; each current plan prices from its own members |
| 7 Stars, several current | GD1, GD4 | Stars go up to 16 with current plans counted; a second current plan joins the pages |
| 8 Replaces | GD1 | "Replacing:" groups the pages and packages as the key says |
| 9 Slot picks | GD1 | A click and a pick give the key's order; the picked-over recommendation lapses; numbers stay stable at Issue |
| 10 Transpose | GD1 | Header and labels stay frozen; above 60 plans it refuses, with its tooltip |
| 11 Export viewer | GD1, GD3 | The Excel view equals the downloaded workbook tab by tab; the PDF and Paper views equal the downloaded PDF and Letter PDF; the PowerPoint view shows the PDF's pages, each .pptx text box equals its recorded frame and chart slides are labelled (J.5 B22); nothing is written |
| 12 Client files | GD1, GD3, GD5 | Files match the keys three ways and the old files within tolerance; the Florida Blue pair prints as one column; issuing v2 leaves v1's bytes unchanged |

**Gate C: Stephanie's walk (the old M9).** She builds one real deal on staging beside her spreadsheet and the old app: plan data and typed counts at Milestone 1, a census only after the PHI gate. The outputs are compared line by line and her time is noted. Each finding is labelled a port bug, an intended difference or a new request.

**Exit criteria.** No open port bug in the twelve needs; every figure agrees to the dollar; the keys, the intended-difference register and the Look labels are signed; Gate B passes at both milestones; the PHI checklist is complete before any real member data.

## V.3 The ten biggest risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Client files drift while the four largest painters (about 6,900 lines) are split into small modules | Styles, formulas and layout tokens ported verbatim as data modules; the old writer versions pinned; Fidelity on every painter slice; the intended register |
| 2 | Money math disagrees: rounding, Decimal, composites, packages, priced versions, stop-loss; the old app had two rounding rules (H.5 #9) | All rounding in `quotes/math/`; table tests; signed keys checked three ways; the old app run once on each parity profile |
| 3 | The quote-first path breaks in a module that assumes intake or a census, or when a second current plan arrives | One enrollment and one headcount function; contract 5 in every module that reads them; GD3's two checkpoints; the need-6 walk |
| 4 | Screens or interactions drift: split sheets, the `.btn-primary` fix, rules borrowed from left-out sheets, grid keys, the undo stack, PlanPicker, viewer highlights | One port in the old order with the class sweep and the port proof; pinned tokens; Look with computed-style diffs; Vitest on the key, selection, undo and page modules; scripted walks |
| 5 | AI reads lose quality or err silently; the BAA limits features | Eval thresholds, including silent errors; typed and confirmed values never overwritten; low flags and Undo; real files only after OQ29 |
| 6 | PHI leaks through new paths: Activity `changes`, job results, logs, exception text, file names, whole-file reads | Canaries driven by the `phi` flags; key-only `changes` for PHI; the staging log scan; the PHI gate; the screen switch (OQ22) |
| 7 | The old app keeps changing while we port (two commits landed during planning) | The port follows a named commit (891f1b3); newer old decisions are listed for Daniel before the slice that ports their area |
| 8 | A ruling in O.6 is lost during the build | Slice 1 writes every ruling into plan.md; the import-linter chain; the Q.3 contracts; tests encode each default and name its open question |
| 9 | Lost updates and deadlocks with JSON values on rows (K.5 #1, J.5 B2, F.5 #29) | Deal row first, then owners in chain order; the two-thread tests (contract 8) |
| 10 | Slow screens and a slow suite (old: 3.78 MB payloads, 7 s previews, 11 s headers) | Scaling tests in Fast; Perf budgets on GD-Big; compact flags; stored counts; xdist |

## V.4 Decisions this approach asks for
1. A seed-only `golden` app at the end of the chain, imported only by the seed command and the root conftest.
2. Stephanie signs GD1's and GD2's keys before slice 7, and each later key before the slice that prices it.
3. About $20 a month for Eval runs.
4. Daniel judges each Look label once.
5. pytest-xdist once the serial Fast run passes 45 s.
6. The old app runs read-only in its own Compose project, on synthetic data, until cutover, with a tools image (LibreOffice, poppler) for Recalc and Fidelity; 2V pins the old file writers' versions until then.

## V.5 How this plan was checked
- A read-only script recounted the X.3 tables: 1,446 items, with the verdict totals in the summary.
- Every owner need is traced to plan items and to slices (the traceability table).
- Every slice's Needs point to earlier slices, and every slice builds only in Part O's apps.
- Every conflict the audit found has a ruling in O.6.
- Every X.7 question (and C.6) appears in the consolidated list, merged by topic and placed at the first slice its answer changes.
- An adversarial critique of Parts N–Q raised 18 points. Each was checked against the plan file, the old repo (with its 2026-11-11 commits) and 2V, and each was accepted. Where its fix was changed, the change is stated in place: L136 is built with the portal (slice 54), agenda needs booking (slice 49) and not only commission rates, each golden spec gets a parity profile instead of a separate parity deal, and OQ45 stays at slice 38, where the agent-of-record step arrives.
