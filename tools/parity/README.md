# Old Vantage beside 2Vantage (the parity harness)

plan.md §3.4 and §12.7, Part Q (Q.5). Old Vantage runs at commit `891f1b3` as its own Compose project, read-only, on
synthetic data, so its screens and files can be compared with 2Vantage's on the same golden deal. It is switched off
at cutover (OQ100).

| | Old Vantage (parity) | 2Vantage | Real old app (never touched) |
|---|---|---|---|
| Frontend | http://localhost:4002 | 4001 | 4000 |
| Backend | http://localhost:8005 | 8004 | 8003 |
| Postgres | localhost:5437 (`parity_old`, user `parity`) | 5436 | 5435 |

Compose project `vantage-parity`: its own `db`, `media`, `references` and `static` volumes; the app's containers sit
on an internal network with no route out, and only the `gateway` (nginx) publishes the three ports. The AI key is
`dummy-no-calls` and HTTP proxies point nowhere, so nothing can reach Claude or the internet.

## Commands (Git Bash, from the repository root)

```bash
bash tools/parity/parity.sh export     # git archive 891f1b3 → %LOCALAPPDATA%/2vantage-parity/old-891f1b3
bash tools/parity/parity.sh up         # build the images, start, wait for the old API (first start migrates: ~1 min)
bash tools/parity/parity.sh load       # GD1 and GD2 from golden/specs (or: load GD1)
npm --prefix browser run check-loaded  # both apps' APIs against the spec and its key
bash tools/parity/parity.sh down       # stop (keeps the database); `reset` also drops its volumes
bash tools/parity/parity.sh tools soffice --version   # the tools image (LibreOffice, poppler, the readers)
```

Every command names `-p vantage-parity -f tools/parity/docker-compose.yml`; none touches the 2Vantage containers.

- **Export.** `export_old.sh` exports only the folders the old app needs (its Django project and apps, `frontend`,
  `assets`), from git, never the old working tree. The old commit also tracks meeting notes, reference files and
  client material; the whitelist keeps them out and the script refuses if one would slip in. Override the folder with
  `PARITY_EXPORT_DIR` and the commit with `PARITY_COMMIT`. The code is mounted read-only from there.
- **Load.** `old_loader.py` runs through the old app's `manage.py shell` and reads the same `golden/specs/gdN.json`
  that 2Vantage's `seed_golden` reads (mounted read-only at `/parity/specs`). Each spec's `parity` profile says how
  the deal maps onto the old records and what the old app cannot hold (`golden/specs.py` documents the format). The
  loader rebuilds each deal by name, writes through the old app's own writers, then reads every row back and stops on
  a difference. Each slice that seeds a deal extends the profile and, where needed, the loader.
- **Sign-in.** The loader makes one synthetic admin, `parity-admin` / `parity-only-pw` (override with
  `PARITY_USER` / `PARITY_PASSWORD`). The Look lane signs in with it through the old token API.
- **The tools image** (`Dockerfile`): headless LibreOffice, poppler-utils, openpyxl, pypdf, python-pptx 1.0.2,
  XlsxWriter 3.3.0 and reportlab 4.2.5 (the old writers' versions, V.4 #6). It runs with no network and the
  repository mounted read-only at `/work`. Recalc and Fidelity (both below) run in it.
- **Intended differences** in client files go in `intended.yaml`; screen differences in `browser/look/accepted.json`.

## The Recalc lane (slice 27; plan.md §12.1, §12.6)

```bash
bash tools/parity/recalc.sh            # TEST_DB_NAME=… to pick the backend's test database (default test_recalc)
```

`pytest -m recalc` (proposals/tests/test_workbook_recalc.py) builds the client spreadsheets in the running backend
(GD1, one plan per rate basis with its worked example, the what-if on an unrated tier), holds every stored result to
the test-only evaluator, and writes the files to `/tmp/recalc-out`; the backend has no LibreOffice, so that step skips
there. The script copies the files to `%LOCALAPPDATA%/2vantage-recalc/<time>/` and runs `recalc.py` in the tools image:
each file's cached results are stripped, LibreOffice recalculates it (a throw-away profile set to always recalculate),
and every formula cell must equal the result the app stored (numbers within 1e-9, blank ≡ ""). It exits 1 on any
mismatch. `python tools/parity/recalc.py <folder>` runs the second half alone on any folder of .xlsx files.

## The Fidelity lane (slice 28; plan.md §12.7, Q.2, Q.5)

```bash
python tools/parity/files.py --deals all          # GD1,GD2 … to pick deals; --out <folder>; on the host
python tools/parity/files.py --fetched <folder>   # compare files fetched before (no download)
```

1. **Fetch** (`fidelity/fetch.py`, standard library only, on the host): signs in to old Vantage (:8005, token) and
   2Vantage (:8004, session and CSRF), finds each golden deal by its client's name, and downloads both apps' client
   spreadsheet, PDF and PowerPoint (old `presentation-workbook/`, `proposal-pdf/`, `proposal-deck/`; new
   `proposal/files/{xlsx,pdf,pptx}/`) into `%LOCALAPPDATA%/2vantage-fidelity/<time>/<GDn>/` (`FIDELITY_OUT` or
   `--out`), with `fetch.json` (statuses, the file names the apps gave, refusals). A refused connection or a 5xx is
   retried for 90 s, since both dev servers reload when code changes. Paper (the Letter PDF) joins when 2Vantage
   builds it (slice 30). Old downloads stamp option numbers in the parity database, as the old app always did.
2. **Compare** (in the tools image, no network; `files.py --compare /data`):
   - `xlsx.py`, `xlsx_cells.py`, `xlsx_setup.py`: sheets and the tab the file opens on; rows lined up by their label
     and columns by their headings (`align.py`), formulas, merges, drop-downs and print ranges read through that
     alignment (`refs.py`); per cell the value or formula, number format, font, fill and border; heights ±0.75 pt,
     widths ±0.5 character; frozen panes, zoom, gridlines, conditional fills, pictures, print setup.
   - `pdf.py`, `pictures.py`: pages lined up by title; fonts; words in reading order; each word's box ±0.5 pt, a word
     nudged a few points (`word-offset`) told apart from one the layout moved (`word-position`); the page picture at
     110 DPI (≤0.05% of pixels) where the words agree.
   - `pptx.py`: layouts, master, slide size; slides lined up by title, shapes by kind and text; every paragraph's
     text and run's font (with kerning), each shape's box ±0.5 pt and shadow, charts, notes.
   - `mask.py`, on both sides: dates, Draft and version stamps (with their " · "), ids; footer page and slide numbers
     (a page one file adds is reported once); document authors are not compared.
3. **Judge** (`intended.py`, `report.py`): each difference is labelled from `intended.yaml` (deal, file, a glob over
   its place, optional kind and regular expression) or left unexplained; `report.md` and `differences.json` go beside
   the files. Exit 1 while any difference is unexplained.

The golden deals must be at their parity profile's checkpoint in both apps (GD3: checkpoint A). A walk that moves a
deal (need 6 moves GD3 to B) makes its comparison meaningless until `seed_golden` runs again.

## The screens (browser/)

```bash
npm --prefix browser ci                                   # once: playwright-core, pixelmatch, pngjs, yaml
npm --prefix browser run look -- --screens signin,home,gd1   # both apps; --old-only, --widths 1440, --headed
npm --prefix browser run walk -- --need 0                 # the example walk: sign in, open GD1's Advisor
```

Look drives the installed Chrome (as old `devtools/e2e/_lib.mjs` does) and writes captures, diffs, `report.md` and
the generated `dropped.css` to `%LOCALAPPDATA%/2vantage-look/<time>/` (`LOOK_OUT` overrides). 2Vantage's side signs in
as `LOOK_NEW_USER` / `LOOK_NEW_PASSWORD` (default `golden-admin` / `golden-admin-pw`, a local synthetic superuser).
Screen keys are in `browser/look/screens.mjs`; the hide list for dropped and deferred UI is `browser/look/dropped.yaml`.
