# The PHI gate checklist (plan.md §11.4; slice 47)

Real member data enters 2Vantage only after Daniel signs this checklist (plan.md §11.1, verification.md V.2's exit
criteria). Slice 47 built what the checklist needs. Each item says what it asks, how it is checked, where it stands
and what is still needed.

**Status (2026-11-12): not signed.** Built and checked on the local dev stack. Staging (slice 69) is designed but not
connected, so the items that run on staging are open. The first local canary scan found one leak (item 5): the census
roster search put a name in its URL. It is fixed, and the local scan is now clean.

| # | Item | Status |
|---|---|---|
| 1 | BAAs with every service that stores or processes PHI | Confirmed, by Daniel's answer to OQ29 |
| 2 | The Claude key confirmed under the BAA | Confirmed, by Daniel's answer to OQ29 |
| 3 | Sign-in through the firm's Microsoft 365 accounts; the sign-in lifetime | Built and rehearsed locally. **Open on staging** |
| 4 | The access-log check | **Passes** locally (Fast lane) |
| 5 | The staging canary scan | Built; **clean locally** after the census search fix. **Open on staging** |
| 6 | The controls of §3.8 | Checked locally; Activity scrub run locally (nothing to scrub). **Open:** the scrub on staging's DB |
| 7 | `AI_PHI_READERS` turned on last | Built; off everywhere |

## 1. BAAs

- **Asks:** a BAA with every service that stores or processes PHI: Google Cloud, Anthropic (the BAA of 2026-11-06
  covers the Messages API without beta features) and Microsoft 365 (its BAA comes with the Data Protection Addendum).
- **Status: confirmed.** Daniel answered OQ29 on 2026-11-12: "live data is allowed in this version; the BAA
  prerequisites are met." That answer is the source for this item. Keep the signed copies with this checklist.

## 2. The Claude key

- **Asks:** Anthropic has confirmed in writing that tools, inline files, effort and caching are covered (OQ29). Until
  then Claude reads only synthetic files.
- **In the code (slice 18):** only `ANTHROPIC_API_KEY` (the Foobalabs organization's key); `ai/client.py` is the
  only importer of the SDK; Messages API only, no beta features, no Files API, files go base64 in each request.
- **Status: confirmed under the BAA.** Source: Daniel's answer to OQ29, 2026-11-12, quoted in item 1.
- Tests, seeds and the Eval corpus stay synthetic, and no build step opens a real client's file (§10.8).

## 3. Sign-in through Microsoft 365

- **Asks:** staff sign in with the firm's Microsoft 365 accounts, so MFA and offboarding live there. The sign-in
  lifetime is settled.
- **Built:** OpenID Connect's authorization code flow with PKCE against the firm's Entra ID tenant
  (`accounts/oidc.py`). The ID token is verified with PyJWT: RS256 only, a key from Entra's published set, this
  tenant's issuer, this app as audience, unexpired, our nonce, the firm's `tid`. A firm account signs in as the one
  active Django user with its email, case ignored (`accounts/firm.py`). Nobody is created: an unknown email, a user
  turned off, or an email two active users share is refused with a sentence on the sign-in page. Turning a user off
  in Django admin ends their session at the next request. `AUTH_PASSWORD_SIGNIN=false` turns username and password off
  for the sign-in page and Django admin, which leaves Microsoft 365 as the only way in. The sign-in page shows
  **Sign in with Microsoft** once `AUTH_OIDC_*` is set.
- **Lifetime:** 12 hours (`SESSION_COOKIE_AGE=43200`). This is OQ107's default, already built. Signing this
  checklist settles it.
- **Checked:** `pytest accounts` (the `test_PHI3_*` tests, against an in-memory fake Entra: refusals, tampered
  tokens, state, PKCE, password sign-in off, a 12-hour cookie). `backend/tests/test_phi_gate.py` covers deploy checks
  vantage.E006 to E008. On 2026-11-12 the sign-in was also rehearsed over real HTTP inside the backend container: the
  app on :8015 talked to a stand-in provider on :8016 through `requests`, golden-admin signed in and landed on `next`,
  the cookie lasted 12 hours, and a forged callback was refused.
- **Open, on staging:**
  1. Register the app in the firm's Entra ID and store its secret (deploy/README.md, step 5b). Fill `ENTRA_TENANT_ID`
     and `ENTRA_CLIENT_ID` in `deploy/staging.env`, then release.
  2. In Entra, require MFA for the app (Conditional Access) and set "Assignment required" for the staff group.
  3. **Done when:** staff sign in on staging with their firm accounts. Each needs a Django user with the same email
     (Django admin).
  4. Set `AUTH_PASSWORD_SIGNIN=false` and release. Then check that a firm account still signs in and that a password
     sign-in is refused, on the sign-in page and on `/admin/login/`.
  5. Calendar the client secret's expiry (24 months at most). An expired secret stops every sign-in.

## 4. The access-log check

- **Asks:** every download or view of a PHI file writes one `downloaded` or `viewed` row with the document id, never
  its name (§3.8).
- **Built:** `backend/tests/test_phi_access.py` (`test_PHI4_…`, Q.9 row 47, on a fresh GD6 at Ready to market). It
  finds the doors the way a person does, from the app's own payloads, and calls each one. That covers every Documents
  file of a PHI kind or one the member-data screen flagged (download, view, sheet view), the census export, template
  and import view, every RFP file flagged PHI and its sheet view, the packet, each email draft, the questionnaire's
  PDF and preview, and the quote board exported with lasers. Each door must write one access row, counted on the
  file's view row when it is a repeat view. The row carries the document id when the file is stored, and neither it
  nor the download's name holds the file's name or a roster name. A file without member data (the RFP cover) writes
  nothing, and "Last updated" never moves.
- **Status: passes** (2026-11-12: 28 doors on GD6). It runs in the Fast lane, so every release runs it (§11.3).
- A new file endpoint joins this check when it is built.

## 5. The staging canary scan

- **Asks:** after a scripted walk with the canary census, a log query over every log of the deployment finds no
  canary (§12.9, Q.8).
- **Built:** `deploy/canary_walk.py` and `deploy/canary_scan.py` (standard library only, like the smoke check), plus
  `deploy/canary_scan.sh` for the dev stack. Each run makes its own canaries (`deploy/canaries.py`): names, a spouse,
  birth dates, SSN, address, city, phone, email, the census file's name and a stop-loss laser. The walk works on a new
  synthetic client and does a person's census work. It uploads, maps and applies the census, opens and searches the
  roster, edits a person (plus three refused edits), downloads and views every file that carries the people (the
  census file, export, template, every RFP census file, the Warner forms, the packet, the drafts), types a laser and
  exports the board with it, then archives the client. On the way it checks that no error body, download name,
  redirect, deal header or feed carries a canary. The log query then searches every log since the walk began, case
  ignored, URL-encoded and JSON-escaped spellings included. It fails when a canary is found, or when the logs do not
  show the walk at all.
- **First local run (2026-11-12, run `tynnfh`):** the walk passed all 36 checks. The log query (51 lines from the
  backend, worker, frontend and db) **found one leak.** The census roster's search sent the searched name in the URL
  (`GET /api/deals/{id}/census/?q=<last name>`), and every request log keeps the URL: runserver's here, gunicorn's
  and Cloud Run's on staging. §3.8 says a search posts its value (E28). Every other canary stayed out of the logs.
- **The fix (slice 47):**
  - The search posts its value: `POST /api/deals/{id}/census/search/` with `{q, page, page_size, show}`, answering
    the census page (`census/views.py` SearchView). `frontend/src/api/census.js` `useCensus` sends a name there.
  - The page's GET ignores a `q`, so an old client cannot narrow by URL.
  - Pinned by `census/tests/test_search.py`, plus the contract rows.
  - The other search boxes were checked and none carries PHI in a URL. Documents Find posts. The Advisor finder
    loads an index and searches it in the browser. Home and Commissions search client and party names, which are not
    PHI.
- **Second local run (2026-11-12, run `epckjb`, `CANARY_PASSWORD=… bash deploy/canary_scan.sh`):** the walk passed
  all 37 checks, the posted search among them. The log query over 47 lines found **no canary**, and the search shows
  only as `"POST /api/deals/218/census/search/"`.
- **Open:** on staging, before real data, and again at Milestone 2's Gate A:

     ```bash
     STARTED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
     # signed in through Microsoft 365 in a browser, copy the sessionid cookie (or use CANARY_PASSWORD before
     # passwords go off):
     CANARY_SESSION=<sessionid> python3 deploy/canary_walk.py --url https://$WEB_HOST --out ~/canaries.json
     sleep 120   # let Cloud Logging catch up
     gcloud logging read "timestamp>=\"$STARTED\"" --project=$PROJECT_ID --format=json > ~/staging-logs.json
     python3 deploy/canary_scan.py --canaries ~/canaries.json ~/staging-logs.json
     ```

     The query reads every log the project keeps: the web and worker services and their request logs, the jobs,
     Cloud SQL and the audit logs. Logs that the token-path exclusion keeps out of storage are not read (§11.2).

## 6. The controls of §3.8

- **Asks:** PHI never reaches logs, Activity, Job steps, error text, file names or URLs. Client files print only
  `client: True` fields and nothing on J.4's never list. The token paths stay out of the logs (§11.2).
- **Checked by:**
  - The per-app canary tests in the Fast lane: census (`census/tests/test_canaries.py`), questionnaire, review, the
    client-file safety canaries (proposals), lasers kept as their key only in Activity (`quotes/tests/test_revert.py`,
    commit c543269), the RFP's printed files.
  - Items 4 and 5 above.
  - Slice 69's token-path filters (`backend/logs.py`, `backend/gunicorn_log.py`, the Cloud Logging exclusion, README
    step 7).
- **The Activity scrub, a step before real data:** `python manage.py scrub_key_only_values` (a dry run) and then
  `--apply`. Before commit c543269, a plan edit recorded `sl_lasers` with its values. This rewrites such rows exactly
  as a new edit is recorded now: the laser becomes a key-only entry, the other keys keep their before and after, and
  the row is no longer revertible. It prints counts and ids, never a value. **Dev DB, 2026-11-12: 0 rows hold laser
  values** (the 4 rows that name `sl_lasers` are already key-only). Run it on staging's database as a one-off job
  (`gcloud run jobs execute $MANAGE_JOB --args=python,manage.py,scrub_key_only_values,--apply`) before real data.
- **Status:** checked locally (the per-app canaries, items 4 and 5, the census search fix). **Open:** the scrub on
  staging's database, and item 5 on staging.

## 7. The PHI-gate switch, last

- **Asks:** `AI_PHI_READERS` is turned on last. Only then do the census, intake and questionnaire readers register
  (O.3.3). The member-data screen follows OQ22.
- **Built:** `ai.registry.register_reader` leaves out a reader of `ai.kinds.PHI_TARGETS` while the switch is off. In
  production, `vantage.E006` fails `check --deploy`, and with it the migrations job, while the switch is on and
  Microsoft 365 sign-in is off or passwords are still on. `AI_MEMBER_DATA_SCREEN` stays off (OQ22: files are read
  whole).
- **Status:** off locally and in `deploy/staging.env`. Tests turn it on (`settings_test.py`) because test data is
  synthetic.

## The order before real data

1. ~~Fix the census search (item 5), and get a clean local canary scan.~~ Done 2026-11-12.
2. Connect staging (deploy/README.md steps 1–8, with step 5b for Entra).
3. Staff sign in on staging with firm accounts (item 3, the slice's "done when").
4. Run the canary scan on staging, and get it clean (item 5).
5. Run `scrub_key_only_values --apply` on staging's database (item 6).
6. Set `AUTH_PASSWORD_SIGNIN=false` and release (item 3).
7. Set `AI_PHI_READERS=true` and release (item 7). `check --deploy` passes only now.
8. Daniel signs below. Then Gate C's census at Milestone 2, and the firm's own work from cutover (OQ100).

Signed for the firm: ______________________ Date: ____________
