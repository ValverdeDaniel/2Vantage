// The Look lane (plan.md §12.7, Q.5): capture named screen states in old Vantage and 2Vantage, and compare them.
//
//   npm --prefix browser run look -- --screens <key|prefix|all>[,…] [--widths 1440,1920] [--old-only] [--headed]
//
// Needs both apps up with the golden deals loaded: 2Vantage (seed_golden) and old Vantage (tools/parity/parity.sh up
// and load). Keys live in look/screens.mjs; a key whose 2Vantage screen is not built yet captures the old side and
// is reported "pending slice N". Output (captures, diffs, report.md, report.json, the generated dropped.css) goes to
// $LOOK_OUT or %LOCALAPPDATA%/2vantage-look/<time>/. Exit 1 when a difference is unexplained or a capture failed.

import fs from 'node:fs';
import path from 'node:path';

import { clientId, dealId, session, signIn } from '../shared/apps.mjs';
import { list, parseArgs, stamp } from '../shared/args.mjs';
import { launch } from '../shared/chrome.mjs';
import { FIXED_NOW, NEW, OLD, OUT, WIDTHS } from '../shared/config.mjs';
import { spec } from '../shared/golden.mjs';
import { capture } from './capture.mjs';
import { classes, pixels, style } from './compare.mjs';
import { loadDropped, writeStylesheet } from './hide.mjs';
import { judge, loadAccepted, write } from './report.mjs';
import { pick } from './screens.mjs';
import { prepareContext } from './steady.mjs';

const args = parseArgs();
const screens = pick(args.screens);
const oldOnly = Boolean(args['old-only']);
const started = new Date();
const runDir = path.join(OUT, stamp(started));
fs.mkdirSync(runDir, { recursive: true });

const dropped = loadDropped();
writeStylesheet(runDir, dropped);
const accepted = loadAccepted();

const sessions = { old: await session('old') };
if (!oldOnly && screens.some((s) => !s.new.pending)) sessions.new = await session('new');

const browser = await launch({ headed: Boolean(args.headed) });
const contexts = new Map();
async function contextFor(app, signedIn) {
  const key = `${app}:${signedIn}`;
  if (!contexts.has(key)) {
    const context = await browser.newContext({ deviceScaleFactor: 1, locale: 'en-US', timezoneId: 'America/New_York' });
    await prepareContext(context);
    if (signedIn) await signIn(context, sessions[app]);
    contexts.set(key, context);
  }
  return contexts.get(key);
}

const ids = new Map();
async function idFor(app, deal, client = false) {
  const key = `${app}:${deal}:${client}`;
  const find = client ? clientId : dealId; // a client page's screen opens the deal's client (slice 67)
  if (!ids.has(key)) ids.set(key, await find(sessions[app], spec(deal).client));
  return ids.get(key);
}

async function shoot(app, screen, width, dir) {
  const signedIn = screen.signedIn !== false;
  const id = screen.deal ? await idFor(app, screen.deal, Boolean(screen[app].client)) : null;
  return capture({ context: await contextFor(app, signedIn), app, screen, dealId: id, width, dir, dropped });
}

const rows = [];
for (const screen of screens) {
  const widths = args.widths ? list(args.widths).map(Number) : WIDTHS[screen.widths || 'default'];
  const dir = path.join(runDir, screen.key);
  fs.mkdirSync(dir, { recursive: true });
  for (const width of widths) {
    const row = { key: screen.key, title: screen.title, width };
    try {
      row.old = await shoot('old', screen, width, dir);
      if (screen.new.pending) {
        row.pending = screen.new.pending;
        row.pending_why = screen.new.why;
      } else if (oldOnly) {
        row.pending = 'old only (--old-only)';
      } else {
        row.new = await shoot('new', screen, width, dir);
        row.pixels = pixels(row.old.file, row.new.file, path.join(dir, `${width}-diff.png`));
        row.classes = classes(row.old.classes, row.new.classes);
        row.style = style(row.old.styles, row.new.styles);
      }
    } catch (error) {
      row.error = String(error.message || error).split('\n')[0];
    }
    row.verdict = judge(row, accepted);
    for (const side of [row.old, row.new]) if (side) side.classes = side.classes.length;
    rows.push(row);
    const detail = row.pixels ? `${(row.pixels.ratio * 100).toFixed(2)}% pixels differ` : row.error || row.old?.file || '';
    console.log(`${row.verdict.padEnd(11)} ${screen.key} @${width}  ${detail}`);
  }
}
await browser.close();

const counts = write(runDir, rows, { started: started.toISOString(), old: OLD.base, new: NEW.base, clock: FIXED_NOW });
fs.writeFileSync(path.join(OUT, 'latest.txt'), `${runDir}\n`);
console.log(`\n${Object.entries(counts).map(([k, v]) => `${v} ${k}`).join(', ')}  ->  ${path.join(runDir, 'report.md')}`);
process.exit(counts.unexplained || counts.error ? 1 : 0);
