# Decisions needed (all open questions, consolidated)

[← Porting plan](README.md)

**How to read this list.** Each question has a default, built until Daniel answers. Questions sit under the first slice their answer changes. Tags name the sources: X-Qn is question n in section X.7 (C.6 for Census).

**Before slice 1: scope and conventions**
- **OQ1 Renewals.** Is the renewal workflow (carrying last year's data, past years, revalidation, renewal history, earlier-year chats, reminders) in this build? *Default:* deferred. [A-Q1, C.6 #1, D-Q11, H-Q3, I-Q7, J-Q10, K-Q11, L-Q4, M-Q2]. 
A. deferred for now
- **OQ2 Client page.** Rebuild it (all years, client-level Overview and Agenda)? *Default:* no; the client statement lives at `/commissions?client=…`. [A-Q2, H-Q10]
A. overview yes, agenda yes, rebuild client page yes but in reality we have prospects new clients and then clients after year 1. first they start off as prospects and we need to be able to transfer them over to new clients and then existing clients. prospects and clients needs to be built out but existing clients does not need to be.
- **OQ3 Access.** Does every producer keep access to every deal? *Default:* yes (A43). [A-Q3]
A. yes
- **OQ4 Work with Claude.** plan.md §10.1 and §15 say AI only stages. Keep the chat, with quote reads by admins and direct people landing at once, with Undo? Defer Claude Unleashed (D-195, widened by D-224), a second proposal model with its own agent, with Claude's row and note tools (J160) meanwhile? Defer lessons and saved readers for admin carrier notes? *Default:* yes to all. [D-Q1, D-Q8, D-Q10, F-Q7]
- **OQ5 Questionnaire.** In scope, with all three forms (Florida Blue 51+, Warner large group, SIIA disclosure)? *Default:* yes. [G-Q1]
a. yes
- **OQ6 Commission ledger.** Are statements, reconciliation, gaps and statement reading in the first build? *Default:* rates, splits, booking and the Book are; slice 50 waits. [H-Q1]
A. No
- **OQ7 Features §15 calls non-goals.** Keep the priced-version composer, saved setups (Mine, Shared, stop-loss settings, census filter sets) and proposal templates? *Default:* kept; bundle templates wait. [F-Q1, F-Q6, J-Q6, C27]
a. im not sure what all of this is use your best judgement
- **OQ8 Deferred outputs.** Do you need Classic, the `/p/` share link, the status report, or Plan my day? *Default:* all deferred; the Work queue stays. [J-Q1, J-Q2, M-Q1, I-Q1]
- **OQ9 Conventions this plan changes.** (a) The chain: questionnaire after quotes, agenda after review, rfp before proposals (so proposals can print who was asked), and a seed-only `golden` app. (b) `quotes/math.py` becomes `quotes/math/`; commission splits shares in its own module but rounds only through `round_decimal`. (c) `CensusFacts` and row `flags` are stored counts, checked against a rebuild. (d) A large app may split `services.py` into a package. *Default:* accept all four. [J-Q15, O.1, O.3.7]
A. the order on the side navbar should be the same as the existing vantage repository but not having a questionnaire should not hinder us from loading in quotes that is why we have the editing summary tiers functionality
**Slice 2 (LOOK-1)**
- **OQ10 Undefined colours.** Undefined tokens (`--muted`, `--accent` and others) rendered as their fallback or inherited colour. Keep that, or use the intended colours? *Default:* keep what rendered. [A.5, F.5 #25, H.6, K.6, L.6, M.5 B27]
A. keep what rendered

**Slice 6 (FND-2)** (OQ101–OQ110 were added by plan.md v2.0, §16, from OQ2's answer and the check against v1.1)
- **OQ101 Prospect to client.** (a) A prospect becomes a New client automatically when a plan on its deal is marked sold, or by hand with Convert to client; un-selling undoes only a conversion the sale made; Back to prospect is refused while a plan is sold. (b) New client → Existing client waits with renewals (when the first plan year ends or the first renewal starts); until then a client is Existing only when created as one, for a group the firm already serves, or set by hand while nothing is sold. (c) The old "New clients" view is labelled "Prospects"; won clients list under Clients, with chips New clients and Existing clients. *Default:* yes to all three (CL1–CL12). [OQ2; plan.md §5.1, §13.11]
- **OQ108 Old constants.** Do the old constants modules import on their own, so plan.md §4's data modules can be generated? *Default:* parse their literals with `ast`; mostly moot from slice 3, when the old app runs in its own Compose project (Q.5). Answered by the developer. [v1.1 §16 #2]

**Slice 7 (ADV-1)**
- **OQ11 Renewal stars.** Once a line has stars, must its renewal have its own star to print? *Default:* yes, the old rule. [F-Q8]
- **OQ12 Several sold plans.** May a line have several sold plans? The old app un-sold the other. *Default:* allowed. [J-Q9]
- **OQ13 Stop-loss order.** May stop-loss plans be reordered with arrows and slot picks? *Default:* no, the old rule (F49). [J-Q5]
A. yes
- **OQ103 Rate-basis examples.** The rate bases with no golden deal (`volume_1000`, `weekly_10`, `payroll_100`) need one worked example each, as v1.1's R2.4 asked. May Stephanie sign them before slice 27, which prints them, while slice 7 pins provisional examples? This adds a gate on Stephanie beyond V.4's GD1 and GD2 keys. *Default:* yes. Answered by Stephanie. [v1.1 R2.4; plan.md §12.6]

**Slice 8 (ADV-2)**
- **OQ110 Copying a plan design.** Copy a plan design from an earlier deal (v1.1's R2.1)? No porting part lists it. *Default:* not in this build; carrying last year's plans waits with renewals (OQ1). [v1.1 R2.1]

**Slice 10 (ADV-4)**
- **OQ14 Carrier nicknames.** Should "UHC" find UnitedHealthcare in the finder and in Find on Documents? *Default:* yes. [E-Q8]
A. yes

**Slice 11 (INT-1)**
- **OQ15 Coverage editors.** Keep both the coverage subcards and the intent card, or merge them? *Default:* both, through one service. [B-Q4]
A. yes
**Slice 12 (CEN-1)**
- **OQ16 SSN.** Optional and never asked on the portal, or required as in the old app? *Default:* optional, masked, never asked. [C.6 #2, L-Q2]
- **OQ17 Required and Waived per deal.** Keep the per-deal overrides for each intake question and census column, which plan.md §15 dropped? *Default:* keep. [B-Q1, C27]
a. keep

**Slice 13 (ADV-5)**
- **OQ18 Typed counts against a later census.** Counts typed before the latest import give way to the census, with "Keep my typed counts" (F91), or typed counts always win (H7)? Keep the builder's EnrollmentStrip too? *Default:* F91; keep the strip. [F91, H.6, D67, J48]
a. yes keep the strip
- **OQ19 Borrowing.** Do typed medical counts also price worksite tier-rated lines, labelled "Borrowed from medical", but not dental and vision? *Default:* yes. [J-Q13, F86]
- **OQ20 Two current plans, one typed figure.** When a renewal brings a second current plan, the Advisor asks to split the line figure, offering the quote's per-plan counts. Should unlinked quotes keep pricing from the whole figure meanwhile? *Default:* no; they ask what they replace. [F88, D67, O.6 #10]
A. no; they ask what they replace
- **OQ21 Which headcount.** The band reads the Advisor's medical enrollment, then intake's enrolled count, then an estimate (the old app put intake first). Agreed, with a warning naming all three? *Default:* yes. [G-Q5, K-Q2, B25]

**Slice 15 (DOC-1)**
- **OQ22 Member-data screen.** Your D-225 turned the old app's screen off for Claude reads, with a switch to bring it back; D52 here always screened. *Default:* follow D-225: the screen still runs at upload, but reads leave flagged pages out only while `AI_MEMBER_DATA_SCREEN` is on. [D52, D49, D-225]
- **OQ23 Remove.** Should Remove archive a file (restorable, values stay linked)? Is a true purge ever needed (a client asking for its PHI to be deleted)? *Default:* archive, plus an admin-only purge. [E-Q1]
- **OQ24 File size.** Do files over 30 MB arrive? *Default:* a 30 MB cap. [E-Q10]
A. no 30 MB cap
- **OQ25 Hidden rows.** Should the sheet viewer show hidden rows and columns greyed? *Default:* yes. [E-Q5]
- **OQ26 File types.** Do wrap, POP and sold-paperwork types wait for close-out and implementation? *Default:* yes. [E-Q6]
- **OQ27 Invoices.** Are invoices PHI, since list bills name members? *Default:* no. [E-Q4]A. no

**Slice 17 (DOC-3)**
- **OQ28 What needs approval.** Only values Claude doubted or the locator could not find (the old app), or every value Claude read (2V's plan)? And Claude never confirms a value itself (D-119)? *Default:* the old meaning; a person always applies. [E-Q2, D-Q6]
A. only the values claude doubted need approval, but even unapproved values shouldn't stop the user from continuing. just give a little flag saying X number of things should be reviewed

**Slice 18 (AI-1)**
- **OQ29 The BAA and the key.** Use only the Foobalabs org's key, with real files only after Anthropic confirms in writing that tools, inline files, effort and caching are covered? Statements too, after that? *Default:* synthetic files until then; statements follow OQ6. [D-Q2, H-Q13]
A. ignore this we are good to test with live data in this version, all prerequisites have been met.

- **OQ30 Printed tier counts.** With no census, should Claude propose a quote's printed tier counts, unticked: as the line's figure, or per current plan when printed per plan? *Default:* yes. [D-Q7]

**Slice 20 (AI-3)**
- **OQ31 Model and caps.** Should the golden-deal trial set the default model, read effort and cost caps, with Opus 5.5 kept to admins and direct people? *Default:* yes. [D-Q3; plan.md §16 #7]

**Slice 21 (AI-4)**
- **OQ32 Need 3.** Recreate the scanned quote in the Advisor ("As quoted"), on Documents beside the file, or both? Should printed rows that match no field reach the client files? *Default:* both screens; client files keep the quote's plan order but the house rows. [D-Q4, D-Q5, F-Q2]

**Slice 22 (AI-5)**
- **OQ33 SBC reads.** Should they wait for review even for direct people? *Default:* yes (D71). [D-Q12]

**Slice 24 (AI-6)**
- **OQ34 AI budget.** Should only admins change a deal's AI budget? *Default:* yes. [D-Q12]

**Slice 69 (STG-1)**
- **OQ105 Staging.** v1.1's M2, staging, was never built and Part P has no slice for it, though V.2 runs Gates B and C on staging. Add slice 69 STG-1 after slice 16, with slice 47 and Milestone 1 waiting on it? *Default:* yes (plan.md §11.1, §13.2). [v1.1 M2]

**Slice 25 (PRO-1)**
- **OQ102 "+ Plan" and "+ Package".** v1.1's "+ Plan" prompt (is a second alternate for the same current plan an option, or bought together?) and its member-built "+ Package" dialog have no porting row; F134 leaves them to the Proposal section. *Default:* keep both as 2V built them; slice 25 places them (F134). [v1.1; F134]
- **OQ35 Drafts.** Files not yet issued carry Draft, option numbers are stamped only at Issue, and an issue stores all three files? *Default:* yes. [J-Q3]
- **OQ36 Option numbers.** Keep the old per-line "Option n" (renewals numbered; current plans and priced versions not) instead of C/R/P labels? *Default:* yes. [J-Q8]
- **OQ37 Recommending a current plan.** Keep your 2026-11-10 rule ("keep" means recommend the renewal; kept lines need no pick), or allow it as the old app did? *Default:* your rule. [J-Q4]

A. allow it as as the old app did

**Slice 26 (PRO-2)**
- **OQ38 Renewal letter figures.** Show the carrier's renewal offer ($/yr, % change) in the renewal blocks (J65) and on the Overview chip (M20)? *Default:* yes. [M-Q8]

**Slice 27 (PRO-3)**
- **OQ39 Hidden carriers.** Does a carrier hidden on Markets checked also leave Compare and All Plans, labelled on screen? *Default:* yes. [J-Q11]
- **OQ40 Stephanie's Excel review.** Her marked-up rows and colours, the disclaimer wording, and whether plan notes, telehealth and Rx mail order print. *Default:* the old formats. [plan.md §16 #3–#5, J.6.11]
- **OQ104 Lasers on client files.** Print laser liability as amounts and list lasers by position, never the claimant ids or initials in `sl_lasers`, which the old stop-loss sheet printed? *Default:* yes (plan.md §3.8, §4.3, §9.13). Also changes slice 36. [v1.1; J.4]
- **OQ41 Firm pages and "Prepared by".** Logo, colour and contact in Django admin; About, figures, calendar and team in an in-app drawer; "Prepared by" from the agent-name rule? *Default:* yes. [J-Q7]

**Slice 33 (PRO-9)**
- **OQ42 Florida Blue 5182 / 5183.** The default is your D-219: two plans in the data, one column in client files, paired on Pages or by Claude when asked. Should the in-network single deductible print "EE $2,500 / PP $5,000" (built) or "$2,500"? *Default:* both figures. [D-Q9, F-Q5, J-Q12]

**Slice 36 (ADV-8)**
- **OQ43 Stop-loss workbook.** Is it still the client document for self-funded deals? *Default:* kept. [J-Q14]

**Slice 37 (AI-7)**
- **OQ44 Rank on a filtered board.** Should Rank clear hand-picked stars outside the filter, as the old app clears the whole line? *Default:* no (F.5 #11). [F-Q3]

**Slice 38 (FND-3)**
- **OQ45 Agent of record and owner.** Does anyone act as agent of record without a login? Is the owner always the primary producer? *Default:* an "Agent of record" field falling back to the owner, then the agency producer; saving a split's primary sets the owner. [M-Q4, H-Q8]
- **OQ46 Archive.** Archive hides the client and its one deal, even a sold one; its links stay readable but refuse writes? *Default:* yes. [M-Q5]
- **OQ47 Client deletion.** Never (405), or admin-only with no sale and no ledger row? *Default:* never; archive instead. [M-Q7]
- **OQ48 Lost reason.** Optional, as on the old screen, or required (plan.md §5.1)? *Default:* optional. [M-Q3]
- **OQ49 Deal size.** A typed "Potential deal size" in the header? *Default:* yes. [I-Q11]
- **OQ106 Contact roles.** Keep the old app's eight, or seven without `partner_agent`, whose split partner is marked on the commission split instead (H13, M81)? B13 keeps eight. *Default:* seven (plan.md §4.6). Also changes slice 40. [B13, H13, M81]

**Slice 39 (INT-2)**
- **OQ50 Blocking errors.** Should error-level checks (bad FEIN, eligible above total) block "Ready to market"? *Default:* no; they warn. [B-Q2]
- **OQ51 Budget target.** Is the Monthly Budget Target the medical premium or all lines? *Default:* a hint with Apply, never prefilled (F139). [F-Q4]

**Slice 40 (INT-3)**
- **OQ52 Going to market.** Should Mark as marketed move the deal to Quoting, and the last Sent tick set "Sent to market"? *Default:* no and no, as today; the Emails card offers the button. [B-Q3, K-Q5]
- **OQ53 Size band at 50.** At exactly 50, does enrolled or ATNE decide, and how would a hand override work? *Default:* 51 or more enrolled is large; the form choice is the only override. [G-Q5, K-Q1; plan.md §16 #9]

**Slice 42 (QST-1)**
- **OQ54 Typed signatures.** Will carriers accept typed names, including staff signing for the officer with written authorization? *Default:* typed names plus the paper-copy route. [G-Q3]
- **OQ55 Reopening.** Who may reopen a signed form? *Default:* any user, with a reason. [G-Q6]
- **OQ56 Q15 and "Double".** Should Florida Blue's Q15 premiums prefill from the Advisor, monthly or annual? Is Warner's "Double" the EE+Spouse rate? *Default:* staff type Q15. [G-Q7]

**Slice 43 (QST-2)**
- **OQ57 Florida Blue copy.** Does underwriting accept the stamped flat copy, or only the Acrobat original (G58)? *Default:* stamped. [G-Q4]
- **OQ58 SIIA disclosure.** Opt-in, or on by default for level-funded and self-funded groups? *Default:* opt-in. [G-Q8]

**Slice 44 (RFP-1)**
- **OQ59 Carrier list.** Please give the full list with each rep. Should Aflac, Kaiser, the Blues or UMR join the 25? *Default:* the 25 on Warner's forms. [K-Q3; plan.md §16 #10]
- **OQ60 Card 1 marks.** Keep both "Confirmed" and "Mark completed"? *Default:* both. [K-Q14]

**Slice 45 (RFP-2)**
- **OQ61 Long rosters.** When a roster passes a template's rows (Warner 500, Aetna 485, UHC 350, Angle 213): split, keep writing, or stop? *Default:* stop with a truthful warning. [K-Q7]
- **OQ62 Nature of Business.** Should Warner's cell print the SIC code, or a new intake description? *Default:* the SIC code. [K-Q8]
- **OQ63 Readiness cards and lens chips.** Keep both, or merge them (X-163)? *Default:* both. [K-Q9]
- **OQ64 Universal census.** It leaves the packet when every picked carrier has its own format and "Other carriers" is empty (reversing D-063 #6)? *Default:* yes. [K-Q13]
- **OQ109 `emp_class` on Warner.** Does `emp_class` fill both Warner columns S and X? *Default:* checked against the workbook when K's data modules are generated. Answered by the developer. [v1.1 §16 #11]

**Slice 46 (RFP-3)**
- **OQ65 Returns inbox.** Which address? *Default:* the deal owner's email until one is set. [K-Q4]
- **OQ66 Who gets PHI documents.** Claims, paper questionnaires and disclosures go only to carriers quoting their lines, to medical carriers when a document has no lines, never to "Other carriers"? *Default:* yes. [K-Q6]
- **OQ67 Channel and cover.** Benefit Central or email only? Can you supply Mark's cover sample? More funding boxes than fully insured, level-funded and ASO? *Default:* email drafts and the built cover. [K-Q10]
- **OQ68 RFP outputs.** The RFP page stops offering five files (reversing D-063 #5): the comparison workbook and client proposal come from the Proposal, the stop-loss workbook from the Advisor, and the benefit guide and contribution model are not built (J99, J168). Agreed? Do carriers ever get the proposal? *Default:* agreed; an off-by-default card attaches the latest issued one. [K-Q12, J-Q15]
- **OQ69 SBCs with no role.** Sent by default? *Default:* listed, unticked, "Role not set". [K-Q15]

**Slice 47 (PHI)**
- **OQ107 Sign-in lifetime.** How long does a sign-in last (plan.md §3.5)? *Default:* 12 hours (`SESSION_COOKIE_AGE`, built). Settled before the PHI gate. [v1.1 §16 #1]

**Slice 48 (COM-1)**
- **OQ70 Who saves a split?** *Default:* all-tier users and the deal's owner. [H-Q6]
- **OQ71 Partner amounts.** Is a flat or PEPM partner amount per deal or per line? Is a referral % from the producer pool or gross? *Default:* per deal; the pool, gross selectable per row. [H-Q7]

**Slice 49 (COM-2)**
- **OQ72 Year for earlier clients.** Which year applies to clients served before the app? *Default:* earlier records, then a typed "year with us", else "year unknown". [H-Q4]
- **OQ73 Own tier.** Do producers see only their own share on the ledger? *Default:* yes; admins see all. [H-Q5]
- **OQ74 Pre-sale basis.** Renewal, then Current, then the starred plan as an estimate? *Default:* yes; after the sale only Sold counts. [H-Q9]
- **OQ75 Two carriers on one line.** One commission record per carrier? *Default:* yes. [H-Q11]
- **OQ76 CAA disclosure.** Who sends it while the close-out bundle is out of scope? *Default:* the back office, by email. [H-Q14]
- **OQ77 Agreements, profiles, payouts.** Do comp agreements, producer profiles, payouts and the Book split return after the MVP? *Default:* yes. [H-Q15]

**Slice 50 (COM-3, if OQ6 says yes)**
- **OQ78 Ledger start.** Import the book of business or the old app's records, or add by hand? *Default:* "Add to book" by hand; a one-off import on request. [H-Q2; plan.md §16 #15]
- **OQ79 Received YTD.** By the date the money arrived, or the month it pays for? *Default:* the arrival date. [H-Q12]

**Slice 53 (REV-1)**
- **OQ80 Second factor.** A phoned PIN only when the page shows census people or questionnaire answers, and for medical or claimant send-backs? Or a PIN on every link (your August 2026 request; plan.md §7.12)? *Default:* the narrowed rule. [L-Q1, G-Q2, M.6; plan.md §16 #13]
- **OQ81 Link life.** Seven days, sliding on save, under a 30-day ceiling, or a fixed 14 days? *Default:* the old sliding rule. [L-Q5]
- **OQ82 Email.** Is copying the link still how it is sent, or should the app send email (codes, nudges, reply notices, tasks)? *Default:* links are copied. [L-Q8, I-Q8]
- **OQ83 Admin switches.** Per-form switches, raised security floors, or editable follow-up days? *Default:* fixed rules and code constants. [L-Q6, I-Q6]

**Slice 54 (REV-2)**
- **OQ84 Client contacts, coverage and lines.** Wait for staff approval, or land directly as before? *Default:* wait. [L-Q3]
- **OQ85 Unapproved answers.** Never print them on carrier files or questionnaire PDFs (the old app did, with a warning)? *Default:* never. [L-Q11]
- **OQ86 Portal logging.** Before real PHI, must every portal open, save and submit be logged with IP and browser? *Default:* link stamps and Activity rows; IP only on the BOR signature. [L-Q10]
- **OQ111 Pending answers across requests.** On an ordinary (not blank) link, a client sees pending answers from any link on the deal, flagged "Updated by someone else on your team", not only from the same request. Limit it to the same request? *Default:* any link of the deal (as built in slice 54). [slice 54 report; L82, L106]

**Slice 56 (REV-4)**
- **OQ87 "＋ Add request".** Should a new custom ask wait in the tray rather than reach the portal at once? *Default:* yes. [M-Q6]

**Slice 57 (REV-5)**
- **OQ88 Census sends by contact.** Keep the contact partition (census columns assigned to contacts, one link each)? The per-employee partition goes either way. *Default:* drop it (L67); if kept, `CensusSettings.rules` stores the contacts and this slice sends the links. [L-Q9, C29, L67]

**Slice 59 (REV-7)**
- **OQ89 Reading client uploads.** After the PHI gate, are clients' census and intake files read automatically (staged), or only when staff click? Is a paper questionnaire read on the link before signing? *Default:* census and intake files read and staged; paper questionnaires only filed. [L-Q7, G-Q9]

**Slice 60 (AGD-1)**
- **OQ90 Quote-first steps.** Once quotes are in, do intake, questionnaire and RFP steps stop leading, and do typed counts stop "Import the census" leading? *Default:* yes. [I-Q2, I-Q3]
- **OQ91 Sold deals.** A sold deal shows the commission step and stays on New clients until its effective date. What ends a deal for you? *Default (changed by OQ101 c):* the sold deal shows its commission step, or "Sold", and the sale moves its client from Prospects to Clients at once, where its row shows that step (I122 as changed; plan.md §13.11). [I-Q4]
- **OQ92 Firm-wide marks.** Do Later and Done anyway apply to everyone? *Default:* yes. [I-Q5]
- **OQ93 Deleting tasks.** May the creator or an admin delete a hand-added task (restorable)? *Default:* yes. [I-Q12]

**Slice 61 (AGD-2)**
- **OQ94 New meanings.** Progress counts the milestones that apply; "Actions completed" adds ticked tasks; sparklines show real figures; sales compare the same days of last month. *Default:* accept. [I-Q9]
- **OQ95 Landing page.** New clients first, with the client list under the Clients pill? *Default (reworded by OQ101 c):* yes, with the old New clients view labelled Prospects. Prospects lists clients whose status is Prospect, with I86's rows and cards; Clients lists new and existing clients, with chips. Also changes slice 4. [I-Q10]

**Slice 62 (OVW-1)**
- **OQ96 Waiting banner.** Move "Waiting on" above the facts (X-84)? *Default:* move it; all else keeps the old order. [M-Q9]

**Slice 65 (DOC-5)**
- **OQ97 Census on Documents.** The full roster beside the file, or only the review list? *Default:* the roster. [E-Q3]
- **OQ98 Scanned pages.** Browser OCR (E25) is built here; until then scanned pages are checked by eye. May it wait? *Default:* built here. [E-Q7]
- **OQ99 Pop-out window.** The pop-out (E69–E71, D128) is built here, as its Keep verdicts say. May it wait? *Default:* built here. [E-Q9]

**Milestone 2 (cutover)**
- **OQ100 Cutover.** Close open requests in the old app first, or keep it read-only until they lapse? Old `/b/` links say "This link has moved". *Default:* no data moves (plan.md §16 #15); the timing is yours. [L-Q12]
