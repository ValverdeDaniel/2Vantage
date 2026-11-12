// The Walk lane (plan.md §12.5, §12.7; Q.2): walk one need in 2Vantage, in the installed Chrome.
//
//   npm --prefix browser run walk -- --need <n> [--headed]
//
// Needs 2Vantage up with the golden deals (seed_golden) and a local superuser (LOOK_NEW_USER / LOOK_NEW_PASSWORD).
// Prints PASS / FAIL per step and writes <need>.json (and a screenshot of a failing step) to
// $LOOK_OUT/walk-<time>/. Exit 0 when every step passed, 1 when one failed, 2 when the walk could not start.

import fs from 'node:fs';
import path from 'node:path';

import { parseArgs, stamp } from '../shared/args.mjs';
import { launch } from '../shared/chrome.mjs';
import { NEW, OUT } from '../shared/config.mjs';
import { spec } from '../shared/golden.mjs';
import { WALKS } from './walks.mjs';

const args = parseArgs();
const need = String(args.need ?? '');
const walk = WALKS[need];
if (!walk) {
  console.error(`No walk for need "${need}". Walks: ${Object.keys(WALKS).map((n) => `${n} (${WALKS[n].title})`).join(', ')}`);
  process.exit(2);
}

const dir = path.join(OUT, `walk-${stamp()}`);
fs.mkdirSync(dir, { recursive: true });
const browser = await launch({ headed: Boolean(args.headed) });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'en-US' });
const page = await context.newPage();
page.setDefaultTimeout(Number(args.timeout || 15000));

const rows = [];
let failed = false;
async function step(what, fn) {
  if (failed) {
    rows.push({ verdict: 'SKIP', what });
    console.log(`SKIP  ${what}`);
    return;
  }
  try {
    await fn();
    rows.push({ verdict: 'PASS', what });
    console.log(`PASS  ${what}`);
  } catch (error) {
    failed = true;
    const shot = path.join(dir, `need-${need}-step-${rows.length + 1}.png`);
    await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
    const detail = String(error.message || error).split('\n')[0];
    rows.push({ verdict: 'FAIL', what, detail, shot });
    console.log(`FAIL  ${what}  (${detail})`);
  }
}

console.log(`Need ${need}: ${walk.title}  (${NEW.base})\n`);
await walk.run({
  page,
  step,
  base: NEW.base,
  user: { name: NEW.user, password: NEW.password },
  spec: walk.deal ? spec(walk.deal) : null,
});
await browser.close();

const file = path.join(dir, `need-${need}.json`);
fs.writeFileSync(file, JSON.stringify({ need, title: walk.title, base: NEW.base, rows }, null, 1));
const count = (v) => rows.filter((r) => r.verdict === v).length;
console.log(`\n${count('PASS')} passed, ${count('FAIL')} failed, ${count('SKIP')} skipped  ->  ${file}`);
process.exit(failed ? 1 : 0);
