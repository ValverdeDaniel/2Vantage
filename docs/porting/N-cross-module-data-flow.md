# Part N — Cross-module data flow

[← Porting plan](README.md)

This part shows how facts move between the apps of Part O. Each fact has one owner, and every other app reads it. The "When" column says how a fact stays current:
- **write**: stored by the owner's service;
- **read**: worked out when asked;
- **count**: a stored count the owner rewrites in the same transaction (O.3.7);
- **commit**: an event sent after the transaction commits;
- **event**: stored once, at a named moment.

## N.1 Facts that cross modules

| Fact | Owner (field or function) | Read by | When |
|---|---|---|---|
| Effective date | `Deal.effective_date`; intake's `target_effective_date` writes it (B1) | every app | write |
| Lines to quote | `Deal.requested_lines`, changed only by `intake.set_intent` (B17) | census, quotes, rfp, commission, proposals | write |
| Stage | `Deal.stage`, moved only by `deals.advance` | header, agenda, overview | write: Quoting on the first landed quote read or RFP send; Proposal at Issue; Sold |
| What a lost deal refuses | `deals.rules.refuses` | quotes, questionnaire, rfp, commission, review, ai | read |
| Deal type | `deals.rules.deal_type` over `opened_as`, frozen at the sale | builder chip (J22), dashboard, overview, commission | read |
| Agent name | `deals.rules.agent_name`: agent of record (from slice 38), then owner, then agency producer | rfp, questionnaire, proposals ("Prepared by"), overview | read |
| Primary contact | `deals.contacts.primary` | rfp, questionnaire officer, review, overview | read |
| Past deal; asks open | `deals.rules.is_past`, `client_asks_open` | questionnaire, rfp, review, overview | read |
| Carriers, aliases, comp labels | `deals/carriers.py`, `deals/comp.py` | finder (F14), Find (E64), intake, rfp, commission | constant |
| Today | `deals.clock.today()`, in agency time | every app | read |
| Live files | `Document.objects`, by kind, role and lines | intake chips and checklist, rfp packet, portal slots, readers, agenda | read |
| Protected files | `Document.protected`, set by Issue and by signing | documents' archive and purge, which refuse them | event |
| Member-data screen | `Document.screen` | access logging, the file chip; ai page ranges only while the screen switch is on (OQ22) | write at upload |
| Open warning | `documents.review_rules.open_warning` | owners' statuses and `flags`, rfp check, review counts, overview | pure; counted in `flags` |
| Sheet windows | `documents.sheets.look` | station, rfp real-file view (K82), Excel preview | read |
| Job state | `ai.Job` (`landed.areas`, plan ids) | browser, agenda (unread quote files), overview, `CensusImport.job` | write |
| Employer facts | approved `Intake.answers` | `quotes.facts.group_facts` (questionnaire, rfp), overview | write |
| Goals, client guidance | intake answers incl. `client_guidance` | Advisor hints (F139), Rank (F111), Claude's context; never client files | write |
| Current coverage, in-force comp | `intake.CurrentCoverage` | `facts.incumbent`, commission, rfp, proposals, overview | write |
| Intent per line | `intake.coverage.intent` | Advisor chip (F13), proposals (kept lines never block), commission | read |
| Readiness, checklist, COBRA | `intake.values.readiness`, `Intake.checklist` | agenda, overview Card 1, rfp, Census tab | read |
| Marketed | `Intake.marketed_at`, first date kept | agenda carrier wait (I54), rfp | write |
| Form choice | `Intake.checklist[item].form_key` | questionnaire (which forms are armed) | write |
| Census counts | `census.CensusFacts` | intake `census_state`, agenda, overview, review counts, rfp | count |
| Tier rollups | `CensusFacts.rollup`, by line and by plan name | `enrollment_for` | count |
| Volumes, FTE, ages, 65+ | `census.rollup` | life and disability pricing, rfp, proposals (J66) | read |
| Carrier-required columns | `rfp.required_columns`, through `carrier_required` | census blanks, review asks | read; blanks refreshed on commit after a pick |
| Plans and membership | `quotes.Plan`, `presented()`, `room()` | proposals, commission, questionnaire rows (G30), rfp `awaiting`, ai | write; pure |
| Plan order | `Plan.sort_order`, read through `order.layout` | board, Pages, deck, workbook, station grid (E37), questionnaire rows | write; layout pure |
| Pairs printed as one column | `Plan.pair_of` (D-219) | `room()` (a pair counts once), Pages, client files, option numbers | write |
| Stars | `Plan.starred`, `star_reason`, `starred_by/at` | board and station heads (E40), Rank; never client files | write |
| Enrollment used | `enrollment_for` | every premium, proposals, commission basis (H7), overview check (M67) | read |
| Headcount | `facts.enrolled_headcount` | intake tier, questionnaire band, rfp band and printed count, overview tier | read |
| Group facts, incumbent, cross-check | `quotes.facts` | questionnaire prefill, rfp, commission, overview | read |
| Figures | `quotes.math`, `package()`, `deal_state` | proposals, commission, questionnaire Q15 | read |
| SIIA disclosure state | `quotes.providers.disclosure_state`, filled by questionnaire | stop-loss workbook Binding Notes (G117) | read |
| Sold | `Plan.sold` and `sold_changed` | commission booking, agenda, overview | write, then commit |
| Plan changes | `plans_changed` | proposals' card marks | commit |
| Option numbers | `Plan.option_number`, in proposals' reading order | client files, Pages | event: Issue |
| Printed layout | `quotes.QuoteLayout` | Advisor "As quoted" (F42), Documents (E42) | event: read landing |
| Questionnaire items | the `questionnaire_items` provider | intake checklist, agenda, overview | read |
| Questionnaire files | `rfp_files`, `copy_to_send`, `takes`, `disclosure_needed`, `pdf.build` | rfp | read; the signed copy is filed, protected, at signing |
| Requested rates | `commission.requested_rates` | rfp | read |
| Revenue and booking | `commission.summary.facts`, `card(deal, viewer)`, `Record` | overview, agenda | read; records frozen at booking |
| Who was asked | `RfpRequest.sends`, through `asked_by_line` | proposals' Markets checked (J63, K117) | write at send |
| RFP progress | `rfp.summary.facts` | agenda, overview | read |
| Page split | `proposals.pages` | Advisor Pages and picker (F37, F45), deck, workbook | read |
| Issued proposal | `ProposalIssue` and its Documents | agenda, overview, rfp's optional card | event: Issue |
| Client entries | owners' `client` JSON, written through review | the owner's review queue only | write; approved through the owner |
| Asks, responses, review counts | `review.summary.facts`, `review.rules.next`, `review.rules.badges` | the Review tab and tray (L1, L2, L28, L49), agenda, overview | read |
| Journey, next step, sidebar badges, meters | agenda's `journey/`, its badges from `review.rules.badges` | shell, overview, dashboard | read |
| Notes, Activity | deals | overview timeline, agenda stats, revert | write |

## N.2 The flow along the workflow

```
[intake] facts, intent, checklist --requested lines--> [census] roster --> CensusFacts.rollup
   ^ providers filled from the right: headcount, census_state, questionnaire_items, quote_lines
[census] rollup ------------------> [quotes] enrollment_for, presented, order.layout, package
[quotes] facts.py ----------------> [questionnaire] band, prefill --> signed PDF (documents, protected)
[questionnaire] disclosure state -> [quotes] stop-loss Binding Notes (provider)
[questionnaire] files + [commission] requested rates + [quotes] headcount
                                  --> [rfp] packet, drafts, sends --> advance(quoting)
[rfp] asked_by_line --------------> [proposals] Markets checked
[ai] quote reader --quotes.read_apply--> plans in reading order, QuoteLayout, proposed counts
[quotes] deal_state, pairs -------> [proposals] Pages, files, Issue --> option numbers, advance(proposal)
[quotes] set_sold --sold_changed (on commit)--> [commission] booking --> Records
[review] portal --> owners' client JSON --> approved through each owner
[every app] summary.facts --> [agenda] steps, journey, badges --> shell, [overview], dashboard
```

**The quote-first path.** Quotes often arrive first, so every step works with typed tier counts and no census.
1. "I already have carrier quotes" creates the deal and opens the Advisor with Work with Claude (A14, D43).
2. The read lands plans in the quote's column order (F138) and writes `QuoteLayout` (D66). With no census, it proposes the printed tier counts, unticked: as the line's figure, or per current plan when the quote prints them per plan (D67).
3. Typed or accepted counts drive every premium (`enrollment_for`), the size band (`enrolled_headcount`), expected revenue (H6, H7) and the Proposal (J48, J83). Worksite tier-rated lines borrow the medical counts, labelled as borrowed; dental and vision do not (OQ19).
4. A typed line figure prices a line with at most one current plan. When a renewal brings a second, the Advisor names the plans that lost their price ("N plans have no price: split the counts") and opens the split, with the quote's per-plan counts offered. Unlinked quotes on that line ask what they replace (OQ20).
5. Agenda lists the intake, questionnaire and RFP steps but does not lead with them. "Import the census" does not lead while typed counts drive the Advisor; the enrollment step reads "Add the census, or type enrollment in the Advisor" (I49–I51). Overview never shows "skipped" (M40, M43).
6. When a census arrives, `CensusFacts` is rewritten, and `enrollment_for` prefers it over counts typed before the import (F91). Nothing changes silently:
   - the Advisor shows "Priced from the census now · Keep my typed counts";
   - a booked deal shows "Out of date · Update" (H120);
   - a started questionnaire shows its band notice (G133);
   - mapping becomes the lead step.

## N.3 Keeping it consistent

1. **One owner per fact.** Others read it; none copies it.
   - Headcount, incumbent and enrollment belong to `quotes.facts` and `quotes.math`.
   - Lines to quote belong to `intake.set_intent`.
   - Plan order belongs to `Plan.sort_order`, pairs to `Plan.pair_of`, membership to `presented()`.
   - Open warnings belong to `review_rules`; review counts to `review.rules.badges`.
   - The next step belongs to `agenda.steps`, and ask waits to `review.rules.next`.
   - Who was asked belongs to `RfpRequest.sends`.
   - Client guidance and COBRA belong to intake.
2. **One door per write.** Every write goes through the owner's service. It records Activity with before and after, and returns only what changed. An unchanged write records nothing.
3. **One lock order.** A write across rows or owners locks the Deal row first, then owner rows in chain order, each by id (O.3.7). Review's `mark_document`, the portal save and every revert follow it.
4. **Worked out on read, with four stored exceptions.** Status, readiness, steps, journey, badges, totals, packages, presented sets, bands, `line_states` and preview stamps are never stored. Stored on purpose:
   - counts: `CensusFacts` and `flags` (OQ9);
   - frozen records: commission `Record`, `ProposalIssue` files, signed questionnaire copies, `RfpRequest.sends`;
   - file evidence: `QuoteLayout`, `Document.screen`, `Document.protected`;
   - one-time stamps: `option_number`.
5. **Approved values only.** Rollups, readiness, gates, exports and printed PDFs read stored values. Pending client entries never count (L.6).
6. **Reactions across apps** happen in three ways only:
   - on-commit signals (`sold_changed`, `plans_changed`);
   - providers and registries filled at start-up;
   - direct calls from right to left: rfp calls `census.refresh_facts`; review calls the owners; a landing calls the owner's `apply`; Issue calls `stamp_option_numbers` and `advance`; signing and Issue file protected Documents.

   A failed receiver leaves visible state ("not booked"), never a hidden error.
7. **Stale snapshots are shown, never swapped:** commission's "Out of date" chip, the questionnaire's band notice, the RFP `checks_stamp` with its 409 `?ack=`, and "Draft" until Issue.
8. **Soft deletes.** Plans, members, documents, tasks and notes are removed softly, so Activity, notes, sources and asks never point at nothing.
9. **No GET writes**, except the portal's open stamp and the `downloaded` and `viewed` log rows.
10. **Client files** print only client fields. They never print commission figures, guidance, star reasons, internal notes, sources, document names, review marks, lasers or birth dates (J.4).

## N.4 What each write refreshes

Each hook writes the server's answer into the cache, then invalidates the keys below. "journey" is the shell's one read (O.4).

| Write (owner) | Server side effects | Browser keys refreshed |
|---|---|---|
| Plan values, stars, order, slots, links, pairs, enrollment (quotes) | Activity; `plans_changed` clears proposal card marks | `plans/<line>`, `proposal`, `journey` |
| Mark sold (quotes) | `advance(sold)`; `sold_changed` starts booking | `plans`, `proposal`, `commission`, `header`, `journey` |
| AI landing (ai, through owners) | owner services; `advance(quoting)` on the first quote | the job's `landed.areas`, `journey`, `header` if the stage moved |
| Intake answers, intent, checklist | `deals.set_lines` | `intake`, `journey`; on the Overview also `overview` |
| Census edit or import | `CensusFacts` rewritten | census page, `journey` |
| RFP picks and sends | `refresh_facts` on commit; the first send advances the stage | `rfp`, `journey`; `header` on the first send; checks follow `checks_stamp` |
| Questionnaire answers, signing | the signed copy is filed, protected | `questionnaire/<form>`, `journey`, `documents` |
| Proposal config | its own card marks cleared | `proposal`; previews move by stamp |
| Issue | `issue` job, option numbers, protected files, `advance(proposal)` | `proposal`, `journey`, `header` when the job ends |
| Review decisions, portal saves | owner services | `review/<area>` (its counts included), the owner's area, `journey` |
| Station, Advisor or Overview marks | Activity, never merged | `sources`, `plans/<line>`, `confidence` |
| Agenda marks and tasks | Activity | `agenda`, `overview`, `activity`, `work-queue` |
| Header: lost, owner, archive | Activity | `header`, `journey`, `clients` |
