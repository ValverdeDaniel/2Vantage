# Part B — Intake

[← Porting plan](README.md)

**What it is:** the first stage of a deal, where the firm gathers the employer's facts before going to market:
- 56 questions;
- contacts;
- current coverage;
- the coverage-intent card;
- the marketing checklist (the go-to-market gate);
- the broker-of-record (BOR) signature;
- "Mark as marketed".

Readiness is already computed on read. The old cost came from five things:
- one database row per answer;
- three conflicting ideas of "required";
- two editors for the same facts;
- a gate that recorded nothing when skipped;
- a 1,638-line tab.

## B.1 Files read, in order (one line each)

**Specs and READMEs**

| File (lines) | What it is / what it taught |
|---|---|
| `benefits/README.md` (394) | Seams: `intake_metrics` → checklist; `bor_on_file` is market's one read into radar. |
| `market/README.md` (461) | Per-file contracts for intake, coverage, checklist, validation, intake review, value origin. |
| `benefits/CLAUDE.md` (120) | Layered values, marks, version and edit-lock rules, lost-deal refusal. |
| `PlanningDocs/Benefits/decisions.md` (5,528) | Read D-009, D-011/012, D-030, D-045, D-052, D-053, D-058–D-060, D-064, D-099, D-103, D-104, D-161, D-183, D-202–D-209: the why behind each mechanism. |
| `PlanningDocs/Benefits/review-requests-intake-views.md` (83) | Form / Board / Request / Review views (D-202) and their URL addresses. |
| `PlanningDocs/Benefits/GetToMarketRoadmap.md` (166) | The override-recording gap; "intake is first-time only". |

**Models**

| File (lines) | What it is / what it taught |
|---|---|
| `models/__init__.py` (79) | Re-exports. |
| `models/case.py` (1,878) | Deal intake columns, metrics, value mixins, `CaseField`, `CaseDocument`, `CaseContact`, `CoverageLine`. |
| `models/market.py` (706) | `MarketingAttestation`, `ClientAskItem`, `CensusFieldRequirement`, intake columns of the client link. |

**Rules and services (`market/`)**

| File (lines) | What it is / what it taught |
|---|---|
| `intake.py` (1,055) | The form spec: 56 questions with help, visibility, needs, portal lock, BOR on file, metrics, approve helpers, self-healing rows. |
| `intake_writes.py` (281) | The AI agent's validated writer: `clean_value`, fields, coverage, contacts. |
| `coverage.py` (577) | Coverage intent: matrix, hash, states, two controls, per-line documents, lines off the proposal. |
| `marketing_checklist.py` (615) | Size tiers, items, auto-waive, form resolution. |
| `validation.py` (501) | Intake rules, `parse_comp`, `comp_label`, `parse_date`. |
| Shims `intake.py`, `marketing_checklist.py`, `validation.py`, `claude_readers.py` (5–7 each) | Star re-exports. |
| `intake_review.py` (227) | Intake board payload. |
| `value_origin.py` (231) | Origin words; `write_hand_edit`. |
| `field_request.py` (913) | Rule fold and writer shared with census. |

**Views and payloads**

| File (lines) | What it is / what it taught |
|---|---|
| `urls.py` (362) | Intake routes. |
| `views/market.py` (2,148) | Approve client, intake, contacts, coverage lines, coverage intent, confirm coverage, sign, mark marketed, attestations, ask items. |
| `views/cases.py` (1,256) | Seeding at create; deal PATCH (requested lines, commission rates); case-field edit; review values. |
| `views/ai.py` | Starting the intake job. |
| `views/shared.py` (297) | No-op and revert edit rules. |
| `views/intake_review.py` (62) | Board GET and rules PATCH. |
| `views/portal.py` (1,615–1,655) | The client can sign the BOR and write requested lines. |
| `serializers/market.py` (980) | `intake_payload`, `client_intake_payload`, portal allowlists, form-key resolvers. |
| `serializers/primitives.py` | `line_documents_payload`. |

**AI**

| File (lines) | What it is / what it taught |
|---|---|
| `ai/intake_agent.py` (371) | Work with Claude intake turn: prompt, tools, findings. |
| `ai/claude_readers.py` (4,127, intake parts) | The classic intake reader and staging. |
| `ai/extraction.py` | Keyed vs keyless dispatch; a quote read moves the stage to quoting. |
| `ai/pages.py` | Intake source document types. |
| `ai/page_context.py` | What the chat sees of intake. |

**Frontend**

| File (lines) | What it is / what it taught |
|---|---|
| `services/api/benefitsMarket.js` (455), `benefitsShared.js` (423) | Intake API calls. |
| `IntakeField.jsx` (109) | Typed input shared with the portal and the questionnaire. |
| `intakeFlow.js` (35) | Pure Enter/Tab next-field helpers. |
| `useDealTabStore.js` (191) | Per-deal payload cache. |
| `CoverageDocPicker.jsx` (265) | Document-to-line popover. |
| `CoverageIntentPanel.jsx` (1,112) | Coverage and marketing intent card. |
| `useMarketingChecklist.js` (82), `MarketingChecklist.jsx` (577) | Checklist hook and card. |
| `intakereview/intakeReviewRows.js` (77), `IntakeReviewView.jsx` (458), `IntakeQueue.jsx` (665) | The board and the keyboard review queue. |
| `IntakeTab.jsx` (1,638) | The tab: four views, form, blocks, gate. |
| `useWriteQueue.js` (60), `useRestingFormKeys.js` (34) | Serialized saves; Enter/Tab with no editor open. |
| `StagedScanReview.jsx` | The staged-read diff for intake. |

**Styles**

| File (lines) | What it is / what it taught |
|---|---|
| `benefits-coverage.css` (527) | Coverage card. |
| `benefits.css` (lines 2,202–2,400; 2,968–3,018; 3,537–3,630; 3,981–4,024) | Intake, checklist and coverage base styles. |
| `benefits-census-review.css` (lines 696–760) | Intake board. |

**Readers of intake facts and other context**

| File (lines) | What it is / what it taught |
|---|---|
| `demo_data.py`, `registry.py` | Legacy required case fields; keyless prefill. |
| `renewal.py` (lines 145–380) | What a renewal carries. |
| `commissions/services.py` | Partner contacts; booking reads intake. |
| `market/rfp.py`, `questionnaires/service.py`, `guide/content.py`, `pipeline/plan_math.py`, `pipeline/workbooks.py`, `radar/reminders.py`, `serializers/{journey,overview,client_overview,status_report,pipeline}.py`, `tasks/steps.py`, `commissions/{disclosure,views,lines}.py` | Grep-level reads of who reads which intake field. |
| 2Vantage `CLAUDE.md`, `plan.md` §4.5, §5.2, §6.4, §7.5, §8.6, §15 | Target conventions. |

**Tests:** `market_tests.py` (7,151), `review_intake_tests.py` (223), intake classes in `portal_tests.py` (3,576).

## B.2 Old data model, in brief

- **`CaseField`:** one row per answer: 56 intake keys plus legacy contact email, funding and current carrier.
  - Three layers, confidence, provenance, marks.
  - Section, type, requirement class, options, `visible_if` and help, all copied from the spec onto every row on read.
  - `required` was set only on legal name, FEIN and employee count.
- **`CaseContact`:** 8 roles, primary flag.
- **`CoverageLine`:**
  - line, carrier, funding, effective and renewal dates;
  - plan design, rates and contribution blobs (never edited in the UI);
  - notes, in force, on proposal, rate guarantee;
  - in-force commission as `{type pct|flat|pepm, value}` plus its source.
- **Deal columns:**
  - `requested_lines` (the shopping list, with three writers);
  - `commission_rates`;
  - the coverage confirmation hash, who and when;
  - BOR typed name and when;
  - `marketed_at`.
- **Checklist state:**
  - `MarketingAttestation` per item (checked, note, requirement, client note, form key, who and when);
  - `ClientAskItem` for custom asks;
  - per-deal Required/Waived rules in the census-named `CensusFieldRequirement` with scope `intake`.

## B.3 Functionality inventory and verdicts

### The form

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| B1 | **Four cards, 56 questions:** Employer information 12, Eligibility & workforce 25, Goals & preferences 7, Compliance & regulatory 12.<br>**Types:** text, num, yn, enum, date, money, pct, multi.<br>**Classes:** 8 quote-blocking (legal name, FEIN, SIC, physical address, situs state, states operating, total employees, employee count), 1 conditional, 47 servicing.<br>**Help text** per question. | Keep | `intake/form.py` (data module), served by `/api/meta/`. `target_effective_date` maps to `Deal.effective_date` for every reader (RFP, plan math). |
| B2 | Seven show/hide rules: waive reason when waiving > 0; locations list when multi-location; five "Who handles it?" questions when their parent is Yes. Hidden questions never count, show or get asked; the portal gets them with their rule to reveal live. | Keep; Drop the unused `requested_line_any` rule | `form.visible(question, answers)` |
| B3 | Inputs by type: selects; chips for multi (the UI stored spaces, the AI stored commas); date picker; $/% affixes | Keep; one multi format (a list) | `FieldInput.jsx` (shared with the portal and questionnaire) |
| B4 | Editing: click to edit; text saves on blur, select and date on pick, multi on Done; optimistic; one write at a time; one reload per burst; unchanged writes nothing; `null` reverts | Keep | `intake/services.update_answers`, which returns the changed keys and the new readiness |
| B5 | Keyboard flow: Enter → next question across cards; Tab → next blank needed question; Shift back; Esc drops the draft; an answer that reveals questions waits for the reload; Enter/Tab with no editor open never lands on a button | Keep | `flow.js` (pure) and `useIntakeKeys.js` |
| B6 | Badge per row: Verified ✓ (a person stands behind it), Read by AI (file, page, re-read), Carried, From client, Review (low read), ⚑ Needs checking, Ignored, Missing; rose `*` on needed questions | Keep, **fixed**: "Missing" and the star use the same `needed()` rule (old: Missing on 3 rows, star on 9+) | Badges come from `sources[key]` |
| B7 | Source pin ↗ opens the Documents tab at the value | Keep | Part E |
| B8 | Inline checks (advisory):<br>- FEIN format (error)<br>- eligible > total (error)<br>- enrolled + waiving > eligible<br>- state codes<br>- ALE suggestion at 50+<br>- Form 5500 contradiction (error)<br>- PCORI contradiction<br>- hours 1–40<br>- child age limit 18–30<br>- contact email (error)<br>- renewal date past or more than 12 months out | Keep all; open question B-Q2 on whether errors block "Ready to market" | `intake/validation.py` |
| B9 | Banners: "Required to market" (first 4 gaps plus HR contact / BOR / census); multi-state group; salary & job-title note when life or disability is requested | Keep | — |
| B10 | Header: ready badge (Blocked / Ready to market / Sent to market); "These came from the client" toggle; ✦ Work with Claude; ☑ Select fields → ＋ Ask N, ✓ Approve, Ignore, ⚑ Needs checking, Select all missing; ＋ Ask all N; Mark as marketed / Market anyway ▸ | Keep, **fixed**: "Select all missing" picks needed blanks, not every blank | — |
| B11 | Bulk review bar: approve, ignore or flag every open warning | Keep | — |
| B12 | Per-row ask: ＋ Ask / ✓ In tray / Asked <date> | Keep | Through the Review app's tray (Part L) |

### Contacts and current coverage

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| B13 | Contacts: role (8), name, title, email, phone; main contact (only one); delete; ＋ Add contact; "From client" badge. Readiness needs an HR or benefit admin with name and email. | Keep; **fixed**: email validated, delete asks to confirm | `deals.Contact` at client level (renewal-proof); `contacts_ok` in `intake/values.py` |
| B14 | Current coverage rows: line, carrier, funding, renewal date, notes, in-force commission (pct / flat / PEPM) and its source; ＋ Add coverage line | Keep, **one data path**: the subcards and the intent card edit the same rows through one service (the old app had two editors of the same facts) | `intake.CurrentCoverage`; `intake/services.save_coverage` |
| B15 | Plan design, rates and contribution blobs on coverage rows (never edited in the Intake UI) | Drop: current plans in the Advisor hold this data | — |

### Coverage and marketing intent card

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| B16 | Rows for every line with coverage or requested, in canonical order. Columns: Line (state label, hint, one-click "No" on unanswered rows, note chip), In force, Current plan, Documents, This year (Shop it / Keep as-is / Leave off), ×. Unanswered rows are amber. | Keep | `CoverageIntentCard.jsx`, same look (`benefits-coverage.css`) |
| B17 | Two controls write three facts: in force, shopping (→ `requested_lines`), on proposal. Bulk and single, all-or-nothing. Remove deletes the line's rows and takes it off the shopping list. | Keep, **one writer**: `requested_lines` changes only through one service, also used by the header Lines picker and the Lines-to-quote chips | `intake/services.set_intent` → `deals.services.set_lines` in one transaction |
| B18 | Select-all tri-state header checkboxes; "＋ guarantee" date under Keep; per-line note chip (not part of confirmation) | Keep | — |
| B19 | "＋ Add a line…" (a gap line, not in force) | Keep | — |
| B20 | Confirm coverage & intent, Confirm again, Reopen. Badges ✓ Confirmed / ⚠ Changed since confirmed / Not confirmed; footer counts; confirmed by and when. | Simplify: store the confirmed decisions as readable JSON; "confirmed" = the decisions still equal today's (same self-cancelling behaviour, no hash) | `Intake.intent_confirmed` |
| B21 | Documents per line: renewal, invoice and SBC chips, needed only when a line is in force and shopped. An unscoped document counts for every line. Split chip (open / picker); file drop uploads with kind and lines in one request; picker re-files and re-scopes; "Every line" toggle. | Keep | `documents` (Part E) plus `intake/coverage.documents_by_line` |
| B22 | Medical row: questionnaire and stop-loss disclosure form pickers (locked once signed) | Keep (the questionnaire is in scope) | Writes the checklist's form choice (Part G) |
| B23 | Collapse state remembered per deal | Keep (localStorage); Drop the walkthrough force-open | — |
| B24 | Downstream rules: lines in play; `line_states` (shopped / presented / gap / dormant); lines off the proposal; incumbent card | Keep; Simplify the gating: with no legacy rows, nothing needs to read "shopped" until confirmed | `intake/coverage.py` (pure) |

### Marketing readiness checklist

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| B25 | Tier from enrolled headcount (declared enrolled → census employees → employee count → total): micro ≤ 10, small 11–50, mid 51–99, 100+; ZIP below 51, home address at 51+ | Keep | `intake/checklist.tier` |
| B26 | Items (each auto, attested or document):<br>- coverage intent (auto, not waivable)<br>- census (auto)<br>- COBRA (attest)<br>- salary & occupation (life/disability)<br>- medical questionnaire (document, "on file" tick, or signed in-app form; label by tier; form by pick or tier)<br>- stop-loss disclosure (optional until picked)<br>- renewal / invoice per line (auto "not needed" when nothing is in force or shopped)<br>- claims (100+ or level/self-funded)<br>- custom asks | Keep, **fixed**: the claims rule also reads the intake answer "self-funded" (old: coverage funding only) | `intake/checklist.py` (pure) |
| B27 | Controls: ⬆ Attach; On file / Confirmed; Not needed; Still needed ▸ with a note the client sees; Undo; ＋ Ask (document / form → tray; census → Census gap view); ＋ Add request; Done / Remove; "last year's copy on file"; meter; Sent-to-market badge | Keep | `Intake.checklist` JSON per item `{checked, by, at, note, requirement, client_note, form_key}`; custom asks are Review asks |
| B28 | The same card on the RFP tab and the Overview; the COBRA tick shared with the Census tab | Keep | One component, one hook |

### Authorizations, lines, readiness

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| B29 | BOR e-sign: typed name stamps who and when; "Signed by…" / "On file from <year>"; client can sign on the portal | Keep, **fixed**: store the signing user; allow clearing | `Intake.bor_*` |
| B30 | BOR on file from an earlier year of the same client | Defer with renewals | — |
| B31 | Compliance uploads (BOR letter, carrier authorization, claims experience, 5500, plan/wrap documents) | Keep | Document kinds |
| B32 | Lines-to-quote chip row | Keep the look; same single writer as B17 | — |
| B33 | Ready state: submitted when marketed; ready when every needed question is verified, contacts OK, census OK (now also error-free), BOR on file, checklist clear; else blocked | Keep | `intake/values.readiness` |
| B34 | Mark as marketed / Market anyway (409 lists gaps, confirm, override) | Keep, **fixed**: lost deals refused for every intake write (not only this one); the skipped items are recorded in Activity; Undo allowed. Open question B-Q3 (stage move) | `intake/services.mark_marketed` |
| B35 | Next action and journey steps: complete intake / market; task steps | Keep | `intake.summary(deal)` |

### Board, Request and Review inside Intake

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| B36 | View pills Form · Board · Request · Review (`?view=`) | Keep the pills and look | Board, Request and Review render the Review app's components scoped to intake (Part L); Intake owns only the Form view |
| B37 | Board: per-question Auto / Required / Waived; note to the client; "Asked in"; origin chip; "client sent something different"; filters; select needed gaps; ＋ Ask N; "Edit on the form ▸"; checklist documents not on file; Waiting panel | Keep | Rules stored as `Intake.rules` JSON (not in a census table); the board lives in Part L |
| B38 | Review queue: from the client / read by AI; A/X/R/E/U/I/C/F keys; approve, correct, keep ours, send back, note, reply, resolve; approve all per group; "Approve N ready" | Keep | Part L |

### AI and the rest

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| B39 | Work with Claude intake turn: tools get intake, read document, write fields, write coverage lines, write contacts, verify intake. Read values land as low-confidence reads; values the producer dictates become hand edits; never overwrites a value a person stands behind; findings list. | Keep (Work with Claude is required; the wave-1 reviewer's "drop" is overruled) | `intake/agent_tools.py` on the shared agent framework (Part D) |
| B40 | Classic intake reader (forced tool; PDF chunks, images, sheets; conflicting reads marked low; staged diff → apply; fills coverage blanks by line, adds new contacts) | Keep as a staged read | Part D reader registry |
| B41 | Keyless "stub" prefill that wrote canned answers onto a real deal as if read from a file | Drop (a bug); tests use fixtures | — |
| B42 | Edit sessions and versions on intake writes | Drop | Activity |
| B43 | Portal intake slice (allowlisted keys, scoped asks, lock rule) | Keep | Part L; one lock rule: origin typed, approved or relayed |
| B44 | Renewal carry of intake | Defer with renewals | — |

## B.4 Data flow

- **In:**
  - census (employee count, census OK);
  - documents (kind, lines);
  - questionnaire (form choice, signed);
  - the review app (asks out, client answers);
  - plans (sold lines, for "lines off proposal").
- **Out, by field:**

| Module | Reads from intake |
|---|---|
| Census | `requested_lines`, in-force lines, COBRA |
| Questionnaire | legal name, addresses, situs state, FEIN, total and eligible employees, ATNE, SIC, years in business; form choice and tier |
| RFP | legal name, addresses, effective date, locations, SIC, FEIN, enrolled / waiving / employee / total counts, ATNE, years in business, waiting period, `requested_lines`, medical funding, checklist and coverage, BOR on file, commission rates, marketed |
| Advisor and Proposal | lines in play, line states, lines off proposal, incumbent facts, hours threshold, domestic partner, effective date, payroll frequency |
| Commissions | requested lines, in-force commission, commission rates, primary contact, addresses |
| Overview and Agenda | readiness, gaps, marketed |

## B.5 Bugs and pain points found

- Three ideas of "required" disagree on screen.
- Two editors for `requested_lines` and for carrier, funding and dates.
- "Market anyway" records nothing and cannot be undone.
- Lost-deal and past-year guards are applied unevenly.
- The producer edit path doesn't clean values, while the AI path does.
- Claims ignores the intake "self-funded" answer.
- The keyless stub writes fake answers.
- "Select all missing" picks the wrong set.
- The chat context reports the BOR from this deal only.
- The 1,638-line tab is shaped by walkthrough anchors.
- No frontend tests.

## B.6 New design

**Django app `intake`** (imports `accounts`, `deals`, `documents`, `ai`)
- `form.py` (data module): sections, questions, help, rules.
- `values.py`: `clean_value` (one cleaner for the producer, AI and portal paths), `visible`, `needed`, readiness.
- Pure rule modules: `validation.py`, `coverage.py`, `checklist.py`.
- `models.py`:
  - `Intake` (deal 1:1): `answers`, `sources`, `rules`, `checklist`, `intent_confirmed`, `bor_name/signed_at/signed_by`, `marketed_at/by`.
  - `CurrentCoverage`: line, carrier, funding, dates, in force, on proposal, guarantee, notes, commission, commission source.
- `services.py`: `update_answers`, `sign_bor`/`clear_bor`, coverage CRUD, `set_intent`, `confirm_intent`/`reopen_intent`, `set_checklist_item`, `mark_marketed`/`unmark`, `apply_read`.
- `selectors.py`: one intake payload with a fixed query count.
- `agent_tools.py`; `summary(deal)`.

**Frontend `deal/intake/`**
- Components: `IntakeTab`, `QuestionCard`, `QuestionRow`, `FieldInput`, `flow.js`, `useIntakeKeys.js`, `ContactsCard`, `CoverageIntentCard`, `CoverageRow`, `DocChip`, `DocPicker`, `ChecklistCard`, `ChecklistRow`, `AuthorizationsCard`, `MarketButton`.
- Styles: the old intake, checklist and coverage rules (`bnf-intake-*`, `bnf-mc-*`, `bnf-cvg-*`, `benefits-coverage.css`), unused selectors removed.

**Tests (behavioural)**
- Visibility rules; validation table; needed / readiness.
- Intent controls round-trip; confirmation cancels on change.
- Checklist tiers and auto-waive; lost-deal refusals; mark marketed records skips.
- One cleaner across paths.

## B.7 Open questions for Daniel

- **B-Q1. Per-deal rules:** keep per-deal Required/Waived per question? The old app had it, plan.md dropped it. Recommended: keep.
- **B-Q2. Blocking errors:** should error-level checks (bad FEIN, eligible > total) block "Ready to market"? The old app only warned.
- **B-Q3. Stage move:** should "Mark as marketed" move the deal to Quoting? The old app moved it only on the first quote read.
- **B-Q4. Keep both coverage editors?** The old Intake page showed both the coverage subcards and the intent card. Keep both, as before, or merge them into the intent card?
