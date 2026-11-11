# Part I — Agenda

[← Porting plan](README.md)

**What it is:** Every deal has an Agenda tab. It lists the steps the deal needs next, worked out on read from every other module, plus tasks people add by hand, in five sections: Up next, Waiting on, Later, Blocked and Done. The same steps drive the deal's next step, the Overview's "Waiting on" banner, its journey and progress, and the dashboard's New clients and Work queue views. People can hold a step back (Later), count it done (Done anyway) or log a follow-up. Nothing on the Agenda changes a deal value.

## I.1 Files read, in order (one line each)

Paths are under `Vantage/` unless marked 2V (`2Vantage/`). Numbers are line counts. (a) = added by the analyst. (f) = opened by the finaliser to settle the challenges.

**Specs and READMEs**
| File (lines) | What it is / what it taught |
|---|---|
| benefits/tasks/README.md (39) | The module contract: steps worked out on read, four stored things, `completed` decided before marks (D-097), no query per deal |
| benefits/README.md (394, grepped) | The module-map row for `tasks/` |
| PlanningDocs/Benefits/task-mode.md (459; 355–368 (f)) | The D-139 spec (2026-10-26): Daniel's five calls, slices 1–9; the bar sits at z 99, under the Admin menu (100) |
| PlanningDocs/Benefits/decisions.md (D-139 at 3718, D-192 at 4920) | Assigned tasks never email anyone; the nudge is stored as a DealTask |
| benefits/radar/README.md (156) | Reminder engine, renewal routing, `?focus=` deep links |
| frontend/src/components/benefits/README.md (421) | Task-mode frontend map; walkthrough anchors |
| benefits/CLAUDE.md (l.11), frontend/CLAUDE.md (l.43, 50) | Task-mode working rules |
| 2V CLAUDE.md (43), plan.md (3432) (a) | The app chain, the write path, `clock.today()`, Activity, the 300-line rule |
| 2V plan.md l.1–12, 240–256, 1576–1612, 1630–1690, 1705–1735, 1870–1885, 1975–1992, 2262–2370, 3115–3130, 3300–3340 (f) | v1.1 (2026-11-10, approved by Daniel). `summary.py` is "read by overview only". §5.9 next-action table and its R4 tests. `Client.relationship` flips at the sale. Note kinds. Document has no read state. `ClientLink.asks`. The §8.3 dashboard is a client list. §15 non-goals include "task queues" and "share links with client selection" |

**Models and migrations**
| File (lines) | What it is / what it taught |
|---|---|
| benefits/models/tasks.py (110) | DealTask (at most one open nudge per link); StepMark (unique per deal, key and kind) |
| benefits/models/radar.py (406) | ClientEvent; ReminderResolution (`until` = snooze); ReminderSettings; rule configs |
| benefits/models/case.py (parts; 293–294) | CaseNote kinds; `deal_size`, `renewal_date`, `marketed_at` |
| migrations 0091_task_mode (73), 0107_dealtask_nudge_link (23), 0018_reminder_config (70) | The stored layer; 0018 seeds the rules with RunPython |
| 2V deals/models.py (94) (a), deals/stages.py (f) | Deal has no `deal_size` and no archive field. Activity has `count` and only one index, (deal, -created_at). Stages: intake, quoting, proposal, sold, lost |

**Rules and services**
| File (lines) | What it is / what it taught |
|---|---|
| benefits/tasks/steps.py (677), read in full (a) | Every label. The carrier wait exists only with no plans (305–327). Census steps come after quotes (330–355). The checklist count excludes only census (463–481). `finish_intake` (501–506) |
| benefits/tasks/marks.py (104) | The only StepMark writer; `NO_DONE_ANYWAY`; refusals |
| benefits/tasks/deal_tasks.py (203) (a) | The DealTask writer; assignee rule; `set_link_nudge`; `nudge_open` |
| benefits/tasks/payload.py (206), check.py (149), `__init__.py` (7) | Payloads; `row_action` (118–143); the re-check and its id parser |
| benefits/radar/reminders.py (1640), reminder_config.py (1159), shims (6, 5) | The 13 rules (listed in I105), severity, the rulebook |
| benefits/serializers/journey.py (557; 280–305, 365–470 (f)), overview.py (505–560; 885–1004 (f)), client_overview.py (540), radar.py (814; 500–814 (f)), case.py (261; 95–140 (f)), status_report.py (420) | `next_action_for`. The journey and its quote-first skip. The `waiting_on` banner cascade. `FOLLOW_UP_DAYS`; `ask_states`. The feed: deal type as of the deal, progress, owner chain. The stat cards |
| benefits/market/intake.py (910–926), marketing_checklist.py (615), client_request.py (`set_nudge` 1555–1600 (f), `earliest_today` 1201), rfp_review.py | Readiness needs `census_ok`. D-192 day rules: today or later, and before the link expires. D-208 |
| benefits/review/link_form.py (461), request_page.py (948–1027), new_link.py (93), board.py (566–666) (f) | `nudge_on`; `people[].nudge`; the banner's entries (blocks_carrier, link_expiring, question, oldest) |
| benefits/pipeline/proposal_review.py, implementation/checklist.py, archive.py | `cards_marked`; ITEM_OWNER and ITEM_AFTER; `live_cases` |
| benefits/ai/extraction.py (846; 741) | Reading a quote moves the deal from intake to quoting |
| management/commands/send_reminder_digest.py (137), seed_clients.py (175) | The daily digest; demo seeding |
| users/permissions.py (88), users/access.py, backend/settings.py, usage/features.py, usage/urls.py | `IsBenefitsUser`; `TIME_ZONE='UTC'`; `tasks.*` usage keys |
| 2V deals/services.py, activity.py, clock.py, values.py, selectors.py; quotes/marks.py, selectors.py; backend/meta.py (a) | Lock, Activity-coalescing and service patterns; `clock.today()` in `AGENCY_TIME_ZONE` |

**Views, routes and payloads**
| File (lines) | What it is / what it taught |
|---|---|
| benefits/views/tasks.py (232) | Seven APIViews: TasksView, TaskPeopleView, DealTaskListCreate, DealTaskDetail, StepMarkListCreate, StepMarkDetail, TaskCheck |
| benefits/views/radar.py (687), requests.py (508), shared.py (297), urls.py (320–362) | Events; resolve and snooze (504); calendar clamp (579). `LinkFormView` is the only nudge writer. `_get_case` ignores archive |
| 2V deals/views.py, deals/urls.py, quotes/urls.py, backend/urls.py (a) | Thin views; `GET users/` |

**AI and assistant**
| File (lines) | What it is / what it taught |
|---|---|
| assistant/platform_notes.py (585–594, 735), platform_map.py (275), policy.py (119) | `WHY_SOURCES`; a bare `?focus=` routes to the client Agenda |

**Frontend**
| File (lines) | What it is / what it taught |
|---|---|
| shared/agenda/agendaRows.js (72), AgendaParts.jsx (361), DealAgendaTab.jsx (117), all read in full (a); taskActions.js (59) | Sections, words, forms and row markup; `window.confirm`; browser-local dates. Later notes go into the deal notes (17–20). Writes made as two requests |
| radar/client/ClientAgendaTab.jsx (419), clientMath.js (135), ClientOverviewTab.jsx, ClientNotificationsTab.jsx (174), ClientHeaderCard.jsx | The client Agenda, its rollup and its links |
| radar/ClientWorkspace.jsx (493), ClientCalendar.jsx (278), ClientsDashboard.jsx (254), ReminderSettings.jsx (690) | Year agenda label; calendar; the client book; rules page |
| shared/CaseWorkspace.jsx (1346; 800–822 (f)), CasesDashboard.jsx (532, read in full (f)), tableSort.js (40) | The Claude strip opens the quote reader. Views and cards (unfiltered by design, 228–249). Invented sparklines (19–22). Size card (426–441). Empty texts (507–523) |
| shared/home/homeRows.js (287 (f)), HomeFilters.jsx (184), WorkQueueTable.jsx (160 (f)), HomeCells.jsx (244 (f)), NewClientsTable.jsx (66), PlanTray.jsx (96) | Stage list, categories, filters, `isDone`, one-per-client collapse; pick column and hint; Archive cell |
| contexts/TaskModeContext.jsx (208), EditSessionContext.jsx (55–72 (f)), BenefitsHomeContext.jsx (123), taskmode/TaskBar.jsx (297) | Plan snapshot in localStorage (MAX_PLAN 100); the old Done waited for in-flight saves; feed cache; the bar |
| shared/RequestNext.jsx (130), LinkSettingsCard.jsx (473–505), useLinkBuilder.js (1485) | "Log a call" made as two requests; the nudge controls |
| App.jsx (368), Navbar.jsx (210), services/api.js, api/benefitsTasks.js, benefitsRadar.js, benefitsShared.js, benefitsReview.js; utils/chromeless.js, usage.js; guides/taskMode.js | Bar mount; Calendar link; API calls (`deleteDealTask` has no caller); walkthrough |
| 2V pages/DealPage/DealPage.jsx (99), DealPage.module.css (f), api/deals.js (220) (a), pages/DashboardPage/ (f) | Tab list; `dealKey`; `invalidateDeal` refetches every deal query except the header; sticky tabs; the client list |
| 2V ui/Menu.module.css, deal/advisor/PlanTable.module.css, pages/Layout/TopBar.module.css, AppLayout.module.css, ui/Toast.module.css (f) | z-index values 50, 30, 100, 1000; sticky plan headers at top 0 |

**Styles**
| File (lines) | What it is / what it taught |
|---|---|
| styles/benefits-tasks.css (247), benefits-taskmode.css (148), benefits-workqueue.css (253) (class lists (a)) | Agenda rows, tray, bar, queue grid; three `.btn-primary` overrides |
| styles/benefits-radar.css (744; 81–131, 358–380, 552 (f)), benefits.css (6275; 74–79, 4645–4660 (f)), benefits-overview.css, App.css (4357; 1–12) | `.bnf-cal-*`, `.bnf-dot-*`, `.bnf-agenda-*`, `.bnf-event-*` and the flash; archive button and link; `.bnf-graph-*`, `.bnf-spark`; `--nav-h`, `--taskbar-h`, `--chrome-top` |

**Tests**
| File (lines) | What it is / what it taught |
|---|---|
| benefits/tests_pkg/tasks_tests.py (959) | 13 test classes plus the StepFixtures mixin (14 classes in all), 52 tests |
| radar_tests.py (2799), existing_client_tests.py, review_link_form_tests.py (LFNudgeReminderTests, 19 tests), story_tests.py, case_tests.py (NextActionTests), market_tests.py (IntakeNextActionTests), review_loop_tests.py (NextStepRoutingTests), review_connection_tests.py, assistant platform_tests.py, devtools/suites.py (806) | Pinned behaviour. CaseHostSourceTests and one RCFrontendContractTests test read source |

**Corrections to the deep report and the draft:**
- views/tasks.py has seven views, not six.
- tasks_tests.py has 13 test classes plus a mixin, and 52 tests.
- There is background work: the digest command.
- The calendar's `?owner=` filters reminders and events by client owner, but nudges by assignee.
- The date-zone bug already had a partial workaround, `earliest_today` (D-208).
- Reading a quote ends stage intake (`extraction.py:741`).
- The deal-task DELETE endpoint has no caller.

## I.2 Old data model, in brief

- **DealTask:** deal FK, title (up to 300 characters), required `due_date`, note, `assigned_to`, `done`/`done_at`/`done_by`, `created_by`/`created_at`. Since D-192 it also has `nudge_link`, with at most one open nudge per link. A task belongs to the deal, never the client.
- **StepMark:** deal, `step_key`, `kind` (later or done), `until`, `sig` (state and label), note, by, at. Unique on (deal, key, kind). Setting one kind deletes the other. Lapsed marks are never cleaned up.
- **ClientEvent:** a client task with a category.
- **ReminderResolution:** client, rule and period. An empty `until` means resolved; a set `until` means snoozed.
- **ReminderSettings** (pk=1: soon 30, horizon 365, digest 45), **ReminderRuleConfig** and **CustomReminderRule**, all seeded by migration 0018.
- **CaseNote** (note, call or email). Later notes and follow-ups are written here.
- **Derived, never stored:**
  - The step dict: id, key, `action_key`, `lead`, label, tab/view, module, owner, state, severity, `sig`, `blocked_reason`, `since`, `due`, `wait_days`, plus the overlays `later_until` and `done_anyway`.
  - `row_action`, `nudge_open`, severity, and the ids `case:`, `step:`, `task:`, `rem:`.

## I.3 Functionality inventory and verdicts

Items added in finalisation are numbered from I119, inside their group. "ch. N" names the review challenge that changed a row.

### The deal's Agenda tab
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| I1 | "Agenda" tab right after Overview in the deal sidebar, no badge -> CaseWorkspace tab `agenda` | Keep | Tab `agenda` after `overview`; route `/deals/:id/agenda` |
| I2 | Title "Agenda" and its subtitle ("Every task on this deal…") | Keep | Same words and classes (`bb-tab-page`, `bnf-ov-titlerow`, `bb-tab-title`, `bb-subtitle`) |
| I3 | "Loading the agenda…" / "Could not load this deal's agenda." | Keep | Same words; InlineError adds Retry |
| I4 | Five sections, each with a ▾/▸ toggle, count and one-line description -> `partitionDeal` in the browser | Simplify | The server puts `section` on each row (`rows.py`). Titles, descriptions and empty words come from `/api/meta/` |
| I5 | Done collapsed by default; an empty collapsed section hidden; "Nothing to do right now." / "Not waiting on anyone." | Keep | Same rules in AgendaSections.jsx |
| I6 | Up next: open tasks by date, then open steps in catalogue order | Keep | Ordered by the server |
| I7 | `?focus=task:<id>` or a step id scrolls to the row and flashes it for 2.2 s | Keep | Same, with `.bnf-agenda-flash`; ids `task:`, `step:`, `nudge:` |
| I8 | A toast after each write; the API's error text shown as is; the whole tab reloads | Simplify | Toast + `lib/errors.js`. Changed (ch. 13): a write invalidates only `['deal', id, 'agenda']`, `['deal', id, 'overview']`, `['deal', id, 'activity']` and `['work-queue']`, never the Advisor's queries |
| I9 | "Year agenda" label on a client's plan-year page | Defer | Part of the existing-client-by-year workspace; renewals are an open question |

### Step rows and their actions
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I10 | Row: date (follow-ups only), severity dot, label, detail, chip, Open ▸, buttons | Keep | Same markup and classes (`bnf-ag-item`, `bnf-ag-row`, `bnf-cal-date`, `bnf-cal-dot bnf-dot-*`, `bnf-cal-main`, `bnf-cal-label`, `bnf-agenda-detail`, `bnf-ag-actions`) |
| I11 | Detail: "Waiting on the client/the carrier", "Back <date> · <who> — <note>", "Marked done by …", the blocked reason | Keep | Built in `rowView.js` from row fields; owner words from meta |
| I12 | Blocked rows muted (opacity 0.6) | Keep | `bnf-ag-muted` |
| I13 | Open ▸ goes to where the work is done -> `case_path` | Keep | One `link_for(deal, tab, view, params)` over the catalogue's tab map |
| I14 | Day labels "Today", "Tomorrow", weekday and date, against the browser's today | Keep | Same labels, measured from the payload's `today` (the agency's date) |
| I15 | Later form: Tomorrow / In 3 days / Next week, a date input (min tomorrow), optional note, Later / Cancel | Keep | Same form. Picks start from the server's `today` (bug 1). Changed (ch. 25): a row may carry `later_max`; on a nudge it is the day before the link runs out. Picks past it are hidden and the input's max is set |
| I16 | Later is firm-wide: the step is hidden from everyone until the day (Daniel's call 3) | Keep | One `StepMark` row per step (ch. 27) |
| I17 | Refusals: missing, done or blocked step (409); lost deal (409); a day not after today (400); bad kind (400) | Keep | `marks.check_mark` (pure), same messages; today = `clock.today()` |
| I18 | A Later note stored on the mark and as a CaseNote "Back to … on <date>: <note>", in two requests | Keep | Changed from Simplify (ch. 24). The mark keeps the note for the detail line. `set_later` also writes the deal Note "Back to “<step title>” on <day>: <note>" in the same transaction, so the note outlives the mark. Activity records the hold without the note |
| I19 | Done anyway asks for confirmation first | Keep | ConfirmDialog with the same words |
| I20 | Done anyway refused on `follow_up_*` and `send_drafts`; the rule existed in both Python and JS | Simplify | One rule in `rules.py`; each row carries `can` flags |
| I21 | Done anyway lapses when the step's words or state change | Keep | `sig` = sha1 of state, label and `basis` (the ids behind a count). A count that returns to the same number with different items no longer brings the mark back. Changed (ch. 28): the same items returning, or an uncounted step (`add_hr_contact`, `get_bor`) left unchanged, keeps the mark. That is intended |
| I22 | Bring back (clears Later); Undo (clears Done anyway) | Keep | DELETE on the mark; Activity keeps before and after |
| I23 | One kind per step | Keep | Unique (deal, step_key); setting one kind replaces the other |
| I24 | Log follow-up (Called/Emailed + "What was said") -> a note, then a Later mark, in two requests | Simplify | `log_follow_up`: a deal Note (call or email) and a Later mark for `wait_days`, in one transaction |
| I25 | Follow-up waits: client ask 3, proposal 7, carriers 10 days | Keep | Constants in `rules.py`, served by meta |
| I26 | Lapsed marks never cleaned up | Keep | Changed from Simplify (ch. 27): ignored on read. There is at most one row per step key, so nothing grows and nothing needs pruning |

### Tasks added by hand
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I27 | Add a task: title ("Add a task… ("send the renewal to HR")"), date (default today), For (deal owner or anyone), Add. The For choice is remembered | Keep | TaskForm.jsx with the same classes (`bnf-event-form bnf-ag-addform`, `bnf-event-title`); default date = server `today` |
| I28 | Title required, up to 300 characters; ISO date required; an active assignee | Keep | `services/tasks.add_task`, same messages |
| I29 | Assignee list from `GET tasks/people/` (filters out COI logins) | Simplify | Reuse `GET users/` (the roles matrix is dropped) |
| I30 | Row: date, colour (overdue red, due within 30 days amber), title, "For <name>" or "Done by …", note, chip "Task" | Keep | Same; `SOON_DAYS = 30` |
| I31 | ✓ ticks (stamps who and when); ↺ reopens (clears both) | Keep | A task is done when `done_at` is set |
| I32 | Later moves the date. The optional note became a separate CaseNote, and the old date was lost | Simplify | `move_task`: the new date plus an optional deal Note, in one transaction; Activity keeps the old and new dates |
| I33 | Editing title, note or assignee, and deleting, existed only in the API; the add form held a note with no input | New | Edit opens TaskForm (title, date, For, note). Changed (ch. 29): Delete is a soft delete (`deleted_at`, `deleted_by`), confirmed first, for the creator or an admin. Activity's revert undoes it (archive-never-delete) |
| I34 | Lost or sold deals still take tasks; archived deals' tasks leave every list | Keep | Same. The archive part waits for the Foundation's `Deal.archived_at` (ch. 8) |

### Nudge reminders and calls logged from Review & requests
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I35 | Nudge row "Nudge <who> about their form", chip "Nudge", Open ▸ to the link's settings -> a DealTask copy | Simplify | Worked out on read from the review link's `nudge` |
| I36 | The day is set, moved or removed in Link settings. It must be today or later and before expiry, with the link on, the request open and the deal not lost | Keep | Owned by Review & requests; `review/services.set_nudge` is the only writer |
| I37 | Later or ✓ on a Nudge row wrote the task directly and skipped every rule | Keep | Fix (bug 7): these call review's `set_nudge` and `finish_nudge` |
| I38 | The row goes quiet when the link is off, submitted, expired or closed, or the deal is lost; it returns when the link is turned on again | Keep | `review.nudge_open(link)` on read |
| I39 | Moving reassigns the nudge to the mover and rewrites its title; clearing deletes it; a ticked nudge stays in Done | Simplify | A `nudge` dict on the link: set replaces it, clear removes it, tick stamps it; the title is worked out on read. Accepted loss (ch. 25): a ticked nudge leaves Done when a new nudge is set on the same link; Activity keeps "Nudge done" |
| I40 | "Log a call" on every banner entry (blocks_carrier, link_expiring, question, oldest): creates a task "Called <name>", then PATCHes it done. A failure leaves an open task | Simplify | Changed (ch. 2): one `POST deals/{id}/tasks/` with `done: true` and today's date, in one transaction. It lands in the Agenda's Done list, as before. It never sets a mark, so it is never refused and never hides a follow-up |

### The step catalogue (engine)
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I41 | Steps worked out on read from module metrics; nothing stored | Simplify | Pure `steps/*` over one facts dict per deal. Changed (ch. 9): the facts come from each app's one batched `facts(deal_ids)`, which Overview reads too |
| I42 | Lead steps kept in line with the separate `next_action_for` cascade by parity tests | Simplify | One rule: the next step is the first live lead step. Changed (ch. 9): plan.md §5.9 `overview/next_action.py` and its R4 tests are retired as well |
| I43 | `revalidate_census` (census carried over from last year) | Defer | Renewal-only |
| I44 | Intake gate steps (complete_intake, checklist:coverage_intent, checklist:<attest>, checklist_ask/client, review_client_answers, review_flagged_answers, add_hr_contact, get_bor, finish_intake), shown only at stage intake | Keep | Same words. Shown while the deal is neither marketed nor sold. They lead only until quotes are in (bug 3). Changed (ch. 19): checklist steps come from intake's checklist rows as intake returns them; attestations are a §15 non-goal, so the old keys are not promised. Census and `medical_questionnaire` are left out of the count because they have their own steps. Intake facts give blockers by key, each blocker maps to one step, and `finish_intake` covers only blockers with no step |
| I45 | "Waiting on the client" for documents or the BOR whenever any ask is out | Keep | Fix (bug 6): waiting only if an open ask asked for those items (`ClientLink.asks`), or a BOR e-sign request is out |
| I46 | The medical questionnaire was hidden in "N checklist items" | New | Its own `questionnaire` step: Send / Waiting on the client for / Review the returned medical questionnaire. Changed (ch. 7b): composed in agenda from intake (needed, form choice), review (asked, `sent_at`) and documents (the returned file and its review state). If that section keeps an in-app form, the questionnaire app's own state is used too |
| I47 | `send_rfp` "Intake ready — market for quotes"; "Sent to market" when done | Keep | From intake `ready` and `marketed_at` |
| I48 | `build_rfp` "m of 5 cards completed"; it vanished when a quote file was uploaded | Keep | Reads the RFP's progress pair; stays until marketed or sold |
| I49 | census_needs_attention, review_mapping, map_census | Keep | Changed (ch. 4): an "enrollment" track that keeps leading after quotes, so a census that arrives late is mapped and picked up |
| I50 | `import_census`, or "Waiting on the client for the census", always lead | Keep | Fix (bug 19): not lead while typed tier counts drive the Advisor. That fact comes from quotes, where the enrollment precedence lives. Changed (ch. 4): once quotes are in and there is no enrollment source, it leads as "Add the census, or type enrollment in the Advisor" (§5.9 words), with links to Census and to the Advisor's tier counts |
| I51 | `fix_census` "Fix N census errors"; `approve_client` "Review N client-provided values" | Keep | Census error count (enrollment track); review's pending values |
| I52 | `answer_client_questions` (not lead) | Keep | Review's open client questions |
| I53 | `read_quotes`: open when a quote file is on file and there are no plans; blocked "After the RFP goes to market"; otherwise waiting on carriers | Keep | Changed (ch. 7a, 23). Open while an unread quote document exists: from the quotes facts, a document of the quote reader's kinds that no plan's `sources` cites. Open ▸ opens Work with Claude's quote reader on those files; the link carries the reader mode and the document ids |
| I54 | `follow_up_carriers` after 10 days at market, only while the deal has no plans | Keep | Fix (ch. 5, bug 22). "Waiting on carrier quotes" and the follow-up count from `marketed_at` whenever no quote document or quote plan has arrived since then, even if an example quote was read earlier |
| I55 | `review_values` "Review N flagged values" | Keep | Plan values that are required and blank, or `to_check` |
| I56 | `build_proposal` "m of n cards completed" (D-113 cards) | Simplify | Built when every presented line's recommendation is covered (§5.4) or a proposal was issued; "Build the proposal — m of n lines recommended" |
| I57 | `share_proposal` "Share the proposal with the client" / "Proposal shared" | Simplify | `issue_proposal`: "Issue the proposal to the client" / "Proposal issued (vN)" |
| I58 | `follow_up_selection`: waiting for under 7 days, then open | Keep | Counted from the latest issue; "nothing sold yet" |
| I59 | `confirm_selection`: the client picked a plan on a share link | Drop | Changed from Defer (ch. 31): nothing triggers it in 2Vantage. Share links with client selection are a §15 non-goal and are not among the owner's needs. The step returns if the Proposal section rebuilds them |
| I60 | `mark_sold`: blocked, then open, then done ("Sold") | Keep | Open ▸ to the Advisor's Sold toggle |
| I61 | `start_implementation` and one `board:<key>` step per row | Defer | Post-sale implementation is out of scope |
| I62 | `build_guide` | Defer | Benefit guides are out of scope |
| I63 | Nothing about commissions after the sale | New | `commission` step: "Enter the commission for N sold lines" (the workflow ends at commissions) |
| I64 | `send_drafts`: requests made and never sent | Keep | Review links never copied |
| I65 | `follow_up_client`: one step across all asks; open at 3 days or on expiry; names what, to whom and how many | Keep | Same words; ask states come from review |
| I66 | Ask steps only before the sale; lost or complete deals have no steps | Keep | Same. Lost deals have no steps; 2Vantage has no complete stage |

### Next step, Overview and progress
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I67 | The Next step row moves past held or done-anyway lead steps. If all are held, it keeps its words and the earliest Later day | Keep | `rows.next_step(steps)`, in this order: the first live lead step; else the first live step of any track; else the held row with its earliest Later day; else the first lead step, shown as done anyway. Fix (bug 12). Changed (ch. 3): marks never make a deal finished (I121) |
| I68 | The Overview banner and the queue show the same next action | Simplify | Overview calls `agenda.selectors.next_step` |
| I69 | Progress bar: the readiness % of the module the action opens | Simplify | Changed (ch. 17): milestones done over the milestones that apply (intake ready, enrollment in, marketed, quotes in, built, issued, sold, commission). Milestones a quote-first deal skipped do not count, as in the old journey |
| I119 | Overview "Waiting on" banner: a third first-match cascade (complete; at market; waiting on the selection; waiting on the employer, with names and opened links; stuck at intake; "the ball is in our court"), using the same 3/7/10 days | Simplify | Added (ch. 10): `rows.waiting(steps)` returns the first waiting lead step with its owner, since, days and severity. Otherwise it returns "with us" and the next step's words. The banner words live in the catalogue; the Overview section renders the banner |
| I120 | Journey stepper ticks (Get to Market, Quote to Close), a fourth rule | Simplify | Added (ch. 10): `rows.journey(steps)` from the catalogue's milestone flags, the same list as I69; the Foundation renders it |
| I121 | A deal is finished when nothing is left before marks (D-097) | Keep | Added (ch. 3): `rows.finished` reads the unmarked steps; lost is decided by stage |

### Work queue and the New clients view
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I70 | Deal rows: Next step words, severity, stage, due (= effective date), owner, progress | Keep | `GET work-queue/` built by `queue/rows.py`. Changed (ch. 12): fetched once under one key. Every row carries `due_in` (days from the agency's today), `held`, `finished`, `type` and `owner_id` |
| I71 | Task rows (open tasks and open nudges), lost and sold deals included | Keep | Same |
| I72 | Reminder and client-task rows | Defer | They come from the Radar |
| I73 | Owner: the commission schedule's primary, then the client owner, then a free-text name | Simplify | Deal owner, else client owner; tasks use their assignee |
| I74 | Next step / All open steps toggle (`&steps=all`) | Keep | `mode` URL param; both lists come in the one payload |
| I75 | Held rows hidden; "Show N held until later" | Keep | The `held` flag on each row |
| I76 | Columns: pick and select-all; Client (avatar, name button, sub-line); Potential deal size; Type; Next action chip; Client response chips; Stage / category pill and bar; Due (overdue red); Owner; Archive | Keep | QueueTable and QueueCells with the same classes. Changed: the pick column and select-all move to AG3, which is deferred (ch. 1). The size column waits for `Deal.deal_size` (ch. 8). Stage pills and labels come from meta, with a pill class added for `proposal` (ch. 20) |
| I77 | Clicking a row opens its link | Keep | Same |
| I78 | Filters: Type chips; Due chips (Overdue / This week / 30 / 90 days / All); client search (prefix, word prefix, substring); owner (including Unassigned); stage and category clear each other; Clear | Keep | Changed (ch. 12): applied in the browser over the one payload, after the split into steps (fixes bug 9). They are plain comparisons on precomputed fields, with no request per chip or letter. Stage options come from meta (ch. 20). Category lists only "Tasks" (hand tasks and nudges, as before); the Upkeep chip is hidden while the Radar is deferred (ch. 21) |
| I79 | "Responses first" (kept in localStorage) | Keep | Same |
| I80 | Complete and lost deals hidden unless asked for; lost deals' tasks still shown | Keep | Finished and lost deals are hidden unless the Sold or Lost stage, or a client search, asks for them. Only then are they fetched (`include=closed`) (ch. 12, 20) |
| I81 | Sorts: client asc, deal size desc, due asc, response desc | Keep | In the browser |
| I82 | Overdue / Due this week cards: unfiltered, but they counted held rows and renewal dates | Keep | Fix (bug 10), changed (ch. 18). The cards still ignore filters, as designed. They count the current mode's rows without held rows and without finished or lost deals, each by its own due date |
| I83 | "Actions completed this week" vs last week (jobs, marketed deals, sold plans, Hub submissions) | Simplify | Milestone Activity rows plus ticked tasks, summing Activity's `count`, because coalesced rows hold several actions (ch. 18). Needs a book-wide Activity index |
| I84 | "Total sales this month" (deal size; month in UTC) vs last month | Keep | Month boundaries in the agency's time zone. Fix (ch. 18): compare the same span of last month. Needs `Deal.deal_size` (ch. 8) |
| I85 | Client responses card (turns on Responses first and scrolls) | Keep | Same |
| I86 | "New clients" landing view: one row per new-business client with its next step, plus cards | Keep | Same payload. Filters and the one-per-client collapse run in the browser (`homeRows.js`) |
| I87 | View pill (New clients, Clients, Work queue), "+ New deal", "Archived" link | Keep | `bnf-viewtab`. Changed (ch. 21): Clients shows the client list (§8.3), restyled with the old book's classes; the Radar's columns are deferred. "Archived" waits for the Foundation's archive page (ch. 8) |
| I88 | Calendar button and Navbar link | Defer | Deferred with the calendar |
| I89 | RefreshChip; BenefitsHomeContext cache | Simplify | React Query |
| I90 | Practice and demo buttons and links (practice client, watch a deal close, the two resets) | Drop | Demo and walkthrough code |
| I122 | Sold deals stayed on New clients through implementation ("intake through sold") | Simplify | Added (ch. 6): implementation is deferred, so a sold deal stays until its effective date passes. It shows its commission step, or "Sold" |
| I123 | Type New business / Renewal, decided as of the deal (D-102) | Keep | Added (ch. 6): "renewal" only when the client has a sold deal with an earlier effective date. Never read from `Client.relationship`, which flips at the sale |
| I124 | New clients card "Potential deal size" (the sum, and "N without a size yet") | Keep | Added (ch. 22); needs `Deal.deal_size` |
| I125 | Empty texts: "No new business in flight — start one with “New deal”.", "Nothing in the queue — start one with “New deal”.", "Nothing matches these filters." | Keep | Added (ch. 22); same words |
| I126 | Row Archive button (an ⓘ in the header; the confirmation names other deals; hidden on sold deals) | Keep | Added (ch. 22); needs the Foundation's archive |
| I127 | Sparklines under the two graph cards (invented curves) | Simplify | Added (ch. 18): same look, real series (last 10 weeks of actions, last 10 months of sales) |

### Plan my day (slice AG3, deferred)
All AG3 items are Defer (ch. 1). plan.md §15 (v1.1, 2026-11-10, approved by Daniel) lists "task queues" as a non-goal. D-139 is older (2026-10-26). None of the twelve needs asks for task mode, and the bar shifts every page. The notes say how to build it if Daniel brings it back.

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I91 | Sticky tray: "N tasks"; By due date / By client; Clear; drag, ▲ ▼ ×; "Begin N tasks ▶". It came with the queue's pick column, select-all and the hint "Tick tasks to plan your day, then Begin." | Defer | When built: PlanTray.jsx with the `bnf-plan-*` classes |
| I92 | The plan was silently cut at 100 tasks | Defer | When built: a toast says so |
| I93 | A snapshot of labels and links kept in localStorage | Defer | When built (ch. 16): store only ids and order; the check returns full rows |
| I94 | A deal row and its own steps could both be picked | Defer | When built: a deal row stores its current step id; duplicates are dropped |

### Task bar (slice AG3, deferred)
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I95 | Begin turns the plan into a session and opens the first task; the plan empties | Defer | When built (ch. 16): Begin moves the plan into the session; Exit puts skipped and unreached ids back |
| I96 | Re-check on Begin or resume; two rules for "finished" | Defer | When built (ch. 15, 16): `POST agenda/check/` is the queue's row builder limited to the named deals: the same row shape, with `gone` for missing ids. It runs after in-flight saves settle. A step held elsewhere answers `later` |
| I97 | Bar under the top bar: 46px, `.has-taskbar`, z-index 99; hidden on chromeless pages, during guides and during the lane C runner | Defer | When built (ch. 14): a z-index token scale (menus above the bar), and `--chrome-top` on every sticky or fixed layer (Advisor, Proposal and viewer, Claude drawer, deal tabs) |
| I98 | Pill, i of N, client and label, due, ◀, Done or Log follow-up, Later, Skip ▶, list, Exit | Defer | When built: Due shows only the task's own date |
| I99 | Done ticks a task and re-checks a step; a "Still open" panel offers Done anyway / Later / Stay | Defer | When built: the Agenda's services, after in-flight saves settle (ch. 15) |
| I100 | Later by kind (task, nudge, step) | Defer | When built: the same services; nudges follow review's rules |
| I101 | Skip, ◀, the list with outcome marks; advancing wraps around | Defer | When built: a task finished elsewhere moves the bar on |
| I102 | Summary "N tasks: x done · y later · z skipped"; Exit confirmation | Defer | When built: ConfirmDialog |

### Client Agenda, Radar, calendar and digest
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I103 | Client Agenda tab (Add to client or deal, Coming up, per-deal panels, Later, Done) | Defer | Lives on the existing-client page, and renewals are open. With one deal per client, the deal Agenda holds every task |
| I104 | ClientEvent client tasks | Defer | Same reason |
| I105 | 13 reminder rules (renewal_kickoff, quoting_checkpoint, renewal_refresh, oe_setup, midyear_review, form_5500, pcori, part_d, erisa_docs, closeout_packet, dq_funding_unverified, dq_missing_5500_doc, commission_gap); resolve, snooze, reopen | Defer | All are post-sale or renewal work; "renewal reminders" is a §15 non-goal |
| I106 | Reminder settings and custom rules | Defer | Deferred with the Radar; `soon_days` becomes a constant |
| I107 | Book calendar | Defer | Its rows are the Radar's |
| I108 | Daily digest email | Defer | Deferred with the Radar |
| I109 | Client nav badge, overview agenda preview, Notifications links, link-client | Defer | They live on the client page |

### Machinery, permissions and tests
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| I110 | `IsBenefitsUser`; anyone can change any task | Simplify | `IsAuthenticated`; the soft delete is limited to the creator or an admin |
| I111 | `tasks.*` usage keys | Drop | Usage analytics is a non-goal |
| I112 | `data-guide-*` anchors, `guides/taskMode.js` | Drop | Walkthrough code |
| I113 | `WHY_SOURCES`, `platform_map` focus routing | Drop | The assistant reading the app's own source |
| I114 | devtools task-mode suite | Drop | In-app test runner |
| I115 | `seed_clients`; seeding by migration 0018 | Drop | Demo code; vocabularies are never seeded |
| I116 | Dead `followup_notes` prefetch; import shims | Drop | No caller. Changed (ch. 29): the deal-task DELETE, which had no caller either, gets one through I33 as a soft delete |
| I117 | Tests that read source (CaseHostSourceTests, one RCFrontendContractTests test) | Drop | Replaced by behavioural tests |
| I118 | Query-count pins (`OPEN_DEAL_QUERIES = 0`) | Simplify | A scaling test: many deals cost the same queries as one |

## I.4 Data flow (in and out, by model, field or function)

**In.** Each app to the left of `agenda` exposes one batched `facts(deal_ids) -> {deal_id: dict}` in its `summary.py`. It runs in a fixed number of queries. Overview reads the same function for one deal (ch. 9). An app not built yet answers "not applicable". Facts carry counts. The ids behind a count (`basis`) are requested only for deals that hold a Done-anyway mark on that step (ch. 11).

| App | Facts | Read by |
|---|---|---|
| deals | stage, lost, `archived_at`, owner, client and client owner, effective_date, `deal_size`, type as of the deal | terminal state, owner, due, type, links, cards |
| intake | ready; blockers by key; checklist rows (key, label, status, satisfy); intent_confirmed; contacts_ok; bor_on_file; BOR request out; `marketed_at`; questionnaire needed and form choice; answers to check | intake gate, send_rfp, get_bor, questionnaire, milestones |
| census | employees, dependents and error count (from a derived per-deal row the census services keep); import state; census file on file; error ids on demand | enrollment steps |
| questionnaire | its own state, if that section keeps an in-app form | questionnaire |
| quotes | quote plans; `last_quote_at`; unread quote document ids; flagged value count; enrollment source (typed, census or none, from the precedence function); presented lines covered; sold lines | read_quotes, carrier wait, review_values, build_proposal, mark_sold, enrollment lead rule |
| commission | sold lines without a rate | commission |
| proposals | latest issue (version, issued_at) | issue_proposal, follow_up_selection |
| rfp | progress pair | build_rfp |
| review | asks (state, first_sent_at, what each asked, names, opened); pending client values; open questions; nudges; response chips | ask, approval and nudge rows, questionnaire, banner, chips |
| documents | returned questionnaire file and its review state | questionnaire |

Today comes from `deals.clock.today()`.

**Out.**
- `StepMark` rows, through `set_later`, `set_done_anyway`, `clear_mark` and `log_follow_up`.
- `Task` rows, through `add_task` (also used by Review's "Log a call"), `update_task`, `move_task` and `delete_task` (soft).
- `deals.Note` (call or email; Later and move notes).
- A review link's `nudge`, only through review's services.
- Activity in area `agenda`.
- No module value or stage is ever written.

**Readers.**
- Overview: `next_step`, `waiting`, `journey`, `progress` (replacing §5.9).
- Foundation: the header's journey (if shown), and the dashboard (Work queue, New clients, stats).
- Review banner: `POST deals/{id}/tasks/` with `done: true`.
- Work with Claude: the browser passes the next step it already holds into the page context. `ai` sits left of `agenda` and never imports it (ch. 7c).

## I.5 Bugs and pain points found (with file evidence)

1. **Date zone.**
   - The server refuses `until <= timezone.localdate()` in UTC (`marks.py:66,76`, `views/radar.py:504`).
   - The browser's `isoIn` uses the local date (`agendaRows.js:7–13`), so an evening Later → Tomorrow returns 400.
   - `date.today()` is also mixed in (`check.py:71`, `serializers/radar.py:559`).
   - Fix: `clock.today()` everywhere; the payload carries `today`.
2. **Re-check parser.** `rsplit` breaks commission_gap ids (`check.py:46–48`). Deferred with AG3 and the Radar. When built, the parser splits from the left.
3. **Reading a quote wipes the intake steps.**
   - The stage leaves intake (`extraction.py:741`), and the gate is tied to stage intake (`steps.py:277`).
   - `build_rfp` vanishes when a quote file is uploaded (`steps.py:286`).
   - Fix: decide from facts, not stage, and add the quote-first lead rule.
4. **No questionnaire step.** It was folded into the checklist count (`steps.py:463–481`). Fix: its own step (I46).
5. **Census-only gaps read "Complete marketing checklist".**
   - Census is excluded from the count (`steps.py:464`), yet readiness needs `census_ok` (`market/intake.py:917–924`).
   - `finish_intake` fires on whatever else blocks (`steps.py:501–506`).
   - Fix: blockers by key, one step each.
6. **Any open ask makes documents and the BOR "waiting"** (`steps.py:475, 495`). Fix: check what the ask asked for.
7. **Nudge Later or tick skips the D-192 rules** (`deal_tasks.update_task` vs `client_request.set_nudge`), and the Later form ignores the link's expiry (`AgendaParts.jsx:17–58`). Fix: review's services, plus `later_max`.
8. **Non-atomic two-request writes:** laterStep, logFollowUp and laterTask in `taskActions.js`, and `RequestNext.logCall`, which leaves an open task when the second request fails. Fix: one transaction each.
9. **Queue filters run before rows are split into steps** (`CasesDashboard.jsx:214–218`), and a deal row's due is its renewal date (`serializers/radar.py:717`). Fix: filter after the split, in the browser.
10. **The Overdue / This week cards count held rows and finished work by renewal date** (`CasesDashboard.jsx:242–249`). Ignoring filters is deliberate (228–229) and stays. Fix: skip held rows and finished deals, and use each row's own due date.
11. **Done anyway comes back** when a count returns to the same number (`steps.py:430`). Fix: `sig` includes `basis`.
12. **Done anyway on the only lead step leaves the row unchanged** (`payload.row_action`, 142–143). Fix: `next_step`, with `finished` decided before marks.
13. **Task bar issues** (deferred with AG3; fixes recorded in I92–I101):
    - The two re-check rules disagree.
    - An item finished elsewhere does not move the bar on (`TaskModeContext.noteOutcomes`).
    - A snooze elsewhere reads as done.
    - Due falls back to the renewal date.
    - Begin empties the plan.
    - The 100-task cut is silent (`TaskModeContext.jsx:28,128`).
14. **Duplicated work.**
    - A mark POST computes the metric chain twice.
    - `?client=` fetches the deals twice.
    - Every read loads the rulebook.
    - `tasks/people/` is fetched on every mount.
    - Fix: facts are read once, and React Query caches.
15. **A query trap.** `review_notes.filter` falls back to a query (`steps.py:359–362`). Pure steps cannot query.
16. **No audit.** Date moves overwrite the old date, and clearing a mark deletes it. Fix: Activity keeps before and after (never titles or notes).
17. **Missing UI for task edit and delete.** The note is in form state with no input for it (`DealAgendaTab.jsx:18`). Fix: I33.
18. **Dead `followup_notes` prefetch** (`journey.py:82–84`).
19. **Quote-first deals are nagged about the census** (`steps.py:330–340`). Fix: the typed-enrollment rule.
20. **The `.btn-primary` width override is repeated three times** (`benefits-taskmode.css:73`, `benefits-tasks.css:104, 206`). Removed. `bnf-ag-section-title` is used but has no rule; it is removed from the markup.
21. **Deferred with the Radar, noted for later:**
    - The client Agenda hides tasks on lost or complete deals.
    - The add-task copy wrongly promises the calendar.
    - Raw rule keys print on screen.
    - A resolved snooze keeps its old `resolved_at`.
    - Snoozing one commission_gap month surfaces the next one.
    - Client-event validation (`bool()`, category length).
    - Calendar quirks: hard-coded 365 and "30 days", clamp 730 vs 1095, owner semantics.
22. **The carrier wait and follow-up vanish once any plan exists** (`steps.py:305–327`). A deal with an early example quote never shows "Waiting on carrier quotes" after it goes to market. Fix: I54.
23. **The sales change compares month-to-date with the whole previous month** (`serializers/case.py:114–118`), so it reads as a fall early in every month. Fix: compare the same span.
24. **The sparklines are invented** (`CasesDashboard.jsx:19–22`, "illustrative"). Fix: real series.
25. **Three next-action cascades** with the same thresholds and different words: `journey.next_action_for`, `overview.waiting_on` (892–1004) and the journey (396–470). Fix: one engine; the banner and the journey read its steps.

## I.6 New design: Django app, models, services, selectors, endpoints, frontend, stylesheets, tests

**App.** A new Django app, `agenda`, right after `review`:

`accounts → deals → documents → ai → intake → census → (questionnaire, placed by its own section) → quotes → commission → proposals → rfp → review → agenda → overview`

- It reads every app to its left. `overview` reads it. `ai` never imports it.
- It owns `Task`, `StepMark`, the step engine and the dashboard feed.
- The `deals` backend never imports it. The dashboard page calls `/api/work-queue/`.

**Models.**
- `StepMark` (ch. 27). Fields:
  - `deal` FK CASCADE (related `step_marks`), `step_key` Char(80), `kind` (later or done);
  - `until` Date null, `sig` Char(40), `note` Text (up to 1,000 characters);
  - `by` FK User SET_NULL, `at` DateTime.
  - Unique on (deal, step_key). It is written with `update_or_create` inside a transaction, which locks an existing row; the unique constraint settles a race. Lapsed rows are ignored on read.
- `Task`. Fields:
  - `deal` FK CASCADE (related `tasks`), `title` Char(300), `due` Date, `note` Text (up to 2,000 characters);
  - `assigned_to` and `done_by` FK User SET_NULL; `done_at` DateTime null;
  - `deleted_at` DateTime null and `deleted_by` FK User SET_NULL (ch. 29);
  - `created_by`, `created_at`, `updated_at`.
  - Index (deal, done_at, due); ordering (due, id). The default manager hides deleted rows.
- Asked of other sections:
  - Review: `ClientLink.nudge` = `{on, by, at, done_at, done_by}`, plus `set_nudge`, `finish_nudge` and `nudge_open`.
  - Foundation:
    - `Deal.deal_size` and `archived_at`, plus an archive page.
    - Note (§6.2).
    - Activity's before/after `changes` and its revert.
    - An Activity index on (area, created_at).
    - A stage pill class for `proposal`.

**Pure modules** (no database access):
- `catalogue.py` is a data module. For each step key it holds the title, tab, view, track (intake, enrollment, quotes, close, after_sale, asks), lead flag, milestone flag and banner words. It also holds section titles, descriptions, empty words and owner words.
- `rules.py` holds:
  - `FOLLOW_UP_DAYS` (client ask 3, decision 7, carriers 10);
  - `SOON_DAYS = 30`, `LATER_PICKS`, `NO_DONE_ANYWAY`;
  - `severity(due, today)`, `due_in(due, today)`, and day and plural words.
- `steps/intake.py`, `steps/enrollment.py`, `steps/close.py`, `steps/asks.py` and `steps/__init__.py` provide `steps(facts, today) -> [step]` in catalogue order.
  - Intake-track steps lead only while no quotes are in.
  - Enrollment steps keep leading; `import_census` does not lead while typed enrollment drives the Advisor.
- `marks.py`: `sig(step)`, `check_mark(step, kind, until, today)`, `apply_marks(steps, marks, today)`.
- `rows.py`: `section`, `finished` (on the unmarked steps), `next_step`, `waiting`, `journey`, `progress`, `task_row`, `nudge_row`.
- `queue/rows.py` (ch. 30) builds the book's rows (deal, step, task and nudge), each with `due_in`, `held`, `finished`, `type`, `owner_id`, `section` and `link`.
- `queue/stats.py` computes actions this week and sales this month, each with its change and a 10-point series.

**Services** (package `agenda/services/`, ch. 30). Each runs in a transaction, locks its row, records Activity and returns only what changed. An unchanged write does nothing. Facts are read once per write, outside the lock.
- `services/marks.py`:
  - `set_later` (with its optional deal Note), `set_done_anyway` and `clear_mark` return `{step, next_step}`.
  - `log_follow_up` returns `{step, note}`.
  - On a nudge row, Later and the tick call review's `set_nudge` and `finish_nudge`.
- `services/tasks.py`: `add_task` (accepts `done`), `update_task`, `move_task` (with its optional Note), `delete_task` (soft).
- Activity summaries use catalogue titles, never task titles, notes or counts. Examples: "Later: Import the census (back Fri 11/20)", "Ticked 3 tasks" (coalesced).
- The before/after values are `kind`, `until`, `due`, `done`, `assigned_to` and `deleted`.

**Selectors:** `facts_for(deals, basis_for=None)`, `deal_agenda(deal)`, `next_step(deal)`, `waiting(deal)`, `journey(deal)`, `work_queue(include)`, `queue_stats()`.

**Performance (ch. 11).**
- The queue reads counts only.
- Census and quotes keep a small derived count on their per-deal row: employees, dependents and errors for census; flagged values for quotes. Their own services write it in the same transaction. A test checks that it equals a fresh count after every service.
- `basis` ids are fetched only for deals with a Done-anyway mark on a counted step.
- Lost deals, and sold deals past their effective date, skip the facts.
- This must be agreed with the census and quotes sections before AG2.

**Endpoints:**

| Method | Path | Body or query | Answer |
|---|---|---|---|
| GET | `deals/{id}/agenda/` | — | `{today, next_step, waiting, journey, progress, rows}` |
| POST | `deals/{id}/agenda/marks/` | `{step_key, kind, until?, note?}` | `{step, next_step}`; 400 or 409 |
| DELETE | `deals/{id}/agenda/marks/{step_key}/` | — | `{step, next_step}` |
| POST | `deals/{id}/agenda/follow-ups/` | `{step_key, kind: call or email, body}` | `{step, note}` |
| POST | `deals/{id}/tasks/` | `{title, due, assigned_to?, note?, done?}` | 201 task row |
| PATCH | `tasks/{id}/` | any of title, due, note, assigned_to, done, move_note | task row |
| DELETE | `tasks/{id}/` | — | 204 (soft); 403 unless creator or admin |
| GET | `work-queue/` | `include=closed` (optional) | `{today, rows, owners, client_names}` |
| GET | `work-queue/stats/` | — | `{actions_week, sales_month}`, each `{total, change_pct, series}` |

`POST agenda/check/` waits for AG3. `/api/meta/` adds `agenda`: sections, step titles, follow-up days, Later picks, soon days, due buckets, type chips and categories. Stages come from `deals`.

**Frontend:**
- `src/api/agenda.js`:
  - Query keys: `['deal', id, 'agenda']` (staleTime 0), `['work-queue', include]` and `['work-queue-stats']`.
  - Agenda writes invalidate only the agenda, overview and activity keys and `['work-queue']` (ch. 13).
  - `invalidateDeal` skips the `agenda` key, as it already skips the header. A journey shown in the header refetches when the tab changes.
- `src/deal/agenda/`: AgendaTab, AgendaSections, AgendaRow, LaterForm, FollowUpForm, TaskForm, `rowView.js`.
- `src/pages/DashboardPage/`:
  - HomePage, which holds the view pill.
  - `newClients/`: NewClientsTable, NewClientCards.
  - `queue/`: WorkQueueTable, QueueCells, QueueFilters, StatCards, Sparkline.
  - `homeRows.js`: filters, sorts, the one-per-client collapse and Responses first, as pure functions; plus `clientSearch.js`.
  - The Clients pill renders the Foundation's ClientTable, restyled.
- Review's banner calls `useAddTask` with `done: true`.

**Styles** (copied verbatim, same class names):
- `benefits-workqueue.css` (`bnf-wq-*`, `bnf-th-*`, `bnf-response-*`, `bnf-responses-*`, `bnf-home-viewbar`, `bnf-nc-*`).
- `benefits-tasks.css` (`bnf-ag-*`, `bnf-wq-modebar/-modehint/-later-toggle/-head`, `bnf-th-action`, `bnf-action-chip`). Its `bnf-plan-*` and `bnf-wq-pick/-picked` rules wait for AG3.
- A new `agenda-rows.css` (ch. 26), cut verbatim from `benefits-radar.css` 81–131, 358–380 and 552, and from `benefits.css` 74–79. It holds `.bnf-cal-date/-dot/-main/-label/-done`, `.bnf-dot-*`, `.bnf-agenda-open`, `.bnf-agenda-detail`, `.bnf-event-form`, `.bnf-event-title`, and `.bnf-agenda-flash` with its keyframes.
- From the Foundation's sheets: `.bnf-viewtab`/`-on`, `.bnf-ov-titlerow`, `bb-*`, `.bnf-graph-*`, `.bnf-spark`, `.bnf-row-archive`, `.bnf-archived-link`, `--nav-h`, `--chrome-top`.
- Not copied: `benefits-taskmode.css` (AG3), the three `.btn-primary` overrides, and `.bnf-client-agenda-row` (deferred).

**Tests** (behavioural; pytest, plus vitest for `homeRows.js`):
- `test_steps`, table-driven over facts dicts:
  - every catalogue state;
  - a quote-first deal: intake steps listed but not leading; census not leading while enrollment is typed; the enrollment words when quotes are in with no enrollment source; a late census making mapping lead;
  - the carrier wait after an example quote;
  - the questionnaire and commission steps, with the questionnaire not counted twice;
  - `finish_intake` firing only for blockers with no step;
  - follow-ups at exactly 3, 7 and 10 days;
  - one follow-up step and one drafts step across many asks;
  - "waiting" only when the ask asked for those items.
- `test_rows`:
  - `next_step` when every step is held, and after Done anyway on the only lead step;
  - Done anyway on `mark_sold` or `commission` never makes a deal finished;
  - the banner and the journey come from the same steps;
  - progress skips the milestones a quote-first deal skipped.
- `test_marks`:
  - Later holds until its day, including at 21:00 Eastern;
  - each refusal and its message;
  - Done anyway lapses when the state, words or items change;
  - marks are firm-wide;
  - an unchanged write records nothing.
- `test_services`:
  - concurrent marks on two steps both survive;
  - `log_follow_up` is all-or-nothing;
  - `set_later` writes its Note in the same transaction;
  - Activity holds no titles or notes;
  - revert restores a date and a deleted task.
- `test_tasks`:
  - add (including `done: true`), tick, reopen, move, edit, and soft-delete permissions;
  - lost deals take tasks;
  - archived deals' tasks leave the lists.
- `test_nudges`: Later follows `set_nudge`, including `later_max`; a nudge goes quiet and comes back; a tick followed by a new nudge.
- `test_queue`:
  - the precomputed fields;
  - type as of the deal;
  - sold deals stay on New clients until the effective date;
  - `include=closed`;
  - stats: same-span sales, Activity `count` summed, series;
  - the scaling check.
- Golden deals: add a quote-first golden deal.

**Slices:**
- **AG1:** the engine and the deal tab, growing as each app's facts arrive. Needs Note (§6.2).
- **AG2:** Overview's next step, banner, journey and progress; the Work queue, New clients and stats.
- **AG3 (deferred):** Plan my day and the task bar.

**Challenge outcomes.** All 31 challenges were accepted. Seven were modified:
- 2: a done task rather than a Call note, to keep the old result.
- 4: mapping a census keeps leading even with typed counts.
- 11: the default chosen is derived counts.
- 12: `due_in` instead of one bucket, because the buckets nest; the collapse stays in the browser.
- 21: nudges stay under "Tasks", as before.
- 25: only `later_max`; Later still starts tomorrow.
- 30: filters left the server, so the server queue holds only rows and stats.

## I.7 Open questions for Daniel

1. plan.md §15 (approved 2026-11-10) lists "task queues" as a non-goal, but D-139 built Plan my day and the task bar at your request. Default: both are deferred (AG3). Do you want them back? Does "task queues" also cover the Work queue itself? Default: the Work queue and New clients stay, so the dashboard looks as before.
2. Once quotes are in, should the intake, questionnaire and RFP steps stop being the Next step? Default: yes; they stay listed.
3. Do typed tier counts stop "Import the census" from leading? Default: yes, and a census that arrives later is still mapped and picked up.
4. What should a sold deal show? Default: the commission step, and a sold new-business deal stays on New clients until its effective date passes. What ends a deal for you?
5. Should Later and Done anyway stay firm-wide, as before? Default: yes.
6. Should the follow-up days (3, 7, 10) and due-soon (30) be code constants (default) or admin-editable?
7. Can the client Agenda, Radar reminders, calendar and digest wait for the renewals decision?
8. Should an assigned task ever email its person? Default: no.
9. Are these new meanings acceptable?
   - Progress = milestones done over the milestones that apply.
   - "Actions completed" = milestone activity plus ticked tasks.
   - The sparklines show real figures.
   - Sales compare the same days of last month.
   - A ticked nudge leaves Done when a new one is set on the same link.
10. Landing page: New clients, as before, with the client list under the Clients pill? Default: yes.
11. Should each deal carry a typed "Potential deal size" again? It feeds the size column, the size card and "Total sales this month". Default: yes, typed in the deal header.
12. May the creator or an admin delete a hand-added task? This is new, and the task can be restored from the activity log. Default: yes.
