// The CSS port proof (plan.md §3.9, Part O.5): every old sheet's files under src/styles/<sheet>/, joined in manifest
// order, equal that sheet at the pinned commit minus the edits listed in port-edits.json. A lint script, not a test:
// it runs on the host, where old Vantage is a sibling checkout, and exits non-zero on any difference.
//
//   node frontend/scripts/port-proof.mjs [--old <path to the old Vantage repo>]
//
// It also checks the manifest (src/styles/index.css) lists every file under each sheet's folder exactly once, in
// order; that no file there is over 300 lines; and that every var() in the ported files names a defined property.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = path.resolve(HERE, '..');
const STYLES = path.join(FRONTEND, 'src', 'styles');
const MANIFEST = path.join(STYLES, 'index.css');
const EDITS = path.join(HERE, 'port-edits.json');
const MAX_LINES = 300;

const toLines = (text) => text.replace(/\r\n/g, '\n').replace(/\n$/, '').split('\n');

// The old sheet minus its edits, as [{ text, old }] where `old` is the old line number (null for inserted lines).
export function expectedLines(oldText, mode, edits) {
  const lines = toLines(oldText);
  const problems = [];
  const at = (n) => lines[n - 1];
  const include = lines.map(() => mode === 'whole');
  const anchor = (e) => {
    const [a, b] = e.lines;
    if (!(a >= 1 && b >= a && b <= lines.length)) problems.push(`edit range ${a}-${b} is outside the sheet`);
    else if (at(a) !== e.first || at(b) !== e.last) problems.push(`edit ${a}-${b} (${e.reason}) no longer matches the old sheet`);
  };
  for (const e of edits.filter((x) => x.kind === 'keep')) {
    if (mode === 'whole') problems.push(`a keep edit (${e.lines}) on a sheet ported whole`);
    anchor(e);
    for (let n = e.lines[0]; n <= e.lines[1]; n++) include[n - 1] = true;
  }
  for (const e of edits.filter((x) => x.kind === 'remove')) {
    anchor(e);
    for (let n = e.lines[0]; n <= e.lines[1]; n++) {
      if (!include[n - 1]) problems.push(`line ${n} is removed twice or was never kept`);
      include[n - 1] = false;
    }
  }
  const text = [...lines];
  for (const e of edits.filter((x) => x.kind === 'rewrite')) {
    const n = e.line;
    if (!include[n - 1]) { problems.push(`rewrite on line ${n}, which is not ported`); continue; }
    const count = text[n - 1].split(e.from).length - 1;
    if (count !== 1) { problems.push(`rewrite on line ${n}: "${e.from}" occurs ${count} times`); continue; }
    text[n - 1] = text[n - 1].replace(e.from, () => e.to);
  }
  const inserts = new Map();
  for (const e of edits.filter((x) => x.kind === 'insert')) {
    if (e.after > 0 && !include[e.after - 1]) problems.push(`insert after line ${e.after}, which is not ported`);
    inserts.set(e.after, [...(inserts.get(e.after) || []), ...e.text]);
  }
  const out = (inserts.get(0) || []).map((t) => ({ text: t, old: null }));
  text.forEach((t, i) => {
    if (include[i]) out.push({ text: t, old: i + 1 });
    for (const x of inserts.get(i + 1) || []) out.push({ text: x, old: null });
  });
  return { lines: out, problems };
}

// Joined files against the expected lines. Blank lines at a file boundary are not compared: a cut never splits a
// rule, and a file starts and ends on content.
function compare(expected, files) {
  const diffs = [];
  let i = 0;
  const skipBlank = () => { while (i < expected.length && expected[i].text.trim() === '') i++; };
  for (const f of files) {
    const got = toLines(fs.readFileSync(f, 'utf8'));
    while (got.length && got[got.length - 1].trim() === '') got.pop();
    let k = 0;
    while (k < got.length && got[k].trim() === '') k++;
    skipBlank();
    for (; k < got.length; k++, i++) {
      const want = expected[i];
      if (!want || want.text !== got[k]) {
        diffs.push({ file: f, line: k + 1, got: got[k], want: want ? want.text : '(end of the old sheet)', old: want?.old });
        return diffs;
      }
    }
  }
  skipBlank();
  if (i < expected.length) diffs.push({ file: files[files.length - 1] || '(no files)', line: 'end', got: '(end of files)', want: expected[i].text, old: expected[i].old });
  return diffs;
}

function readManifest() {
  const imports = [];
  toLines(fs.readFileSync(MANIFEST, 'utf8')).forEach((t, i) => {
    const m = t.match(/^@import\s+['"]\.\/([^'"]+)['"];\s*$/);
    if (m) imports.push({ rel: m[1], line: i + 1 });
    else if (/@import/.test(t)) imports.push({ rel: null, line: i + 1, raw: t });
  });
  return imports;
}

function main() {
  const args = process.argv.slice(2);
  const oldRepo = args.includes('--old') ? path.resolve(args[args.indexOf('--old') + 1]) : path.resolve(FRONTEND, '..', '..', 'Vantage');
  const data = JSON.parse(fs.readFileSync(EDITS, 'utf8'));
  const failures = [];
  const fail = (msg) => failures.push(msg);

  // The manifest: each sheet's folder, in the old order, every file once, numbered in order.
  const imports = readManifest();
  imports.filter((x) => !x.rel).forEach((x) => fail(`index.css:${x.line} is not a plain @import of a sheet file: ${x.raw}`));
  const order = data.sheets.map((s) => s.dir);
  let last = -1;
  const filesByDir = new Map(order.map((d) => [d, []]));
  for (const imp of imports.filter((x) => x.rel)) {
    const [dir, file, ...rest] = imp.rel.split('/');
    const at = order.indexOf(dir);
    if (rest.length || at < 0 || !/^\d\d-[a-z0-9-]+\.css$/.test(file)) { fail(`index.css:${imp.line} imports ${imp.rel}, which is not <sheet>/NN-topic.css for a listed sheet`); continue; }
    if (at < last) fail(`index.css:${imp.line} imports ${imp.rel} after a later sheet: the old order is broken`);
    last = Math.max(last, at);
    filesByDir.get(dir).push({ file, line: imp.line });
  }
  for (const s of data.sheets) {
    const listed = filesByDir.get(s.dir);
    const onDisk = fs.existsSync(path.join(STYLES, s.dir)) ? fs.readdirSync(path.join(STYLES, s.dir)).filter((f) => f.endsWith('.css')).sort() : [];
    if (!onDisk.length) fail(`src/styles/${s.dir}/ has no files`);
    listed.forEach((x, i) => {
      if (x.file !== onDisk[i]) fail(`index.css:${x.line}: ${s.dir}/${x.file} is out of order or does not exist (expected ${s.dir}/${onDisk[i] ?? 'nothing'})`);
      if (Number(x.file.slice(0, 2)) !== i + 1) fail(`index.css:${x.line}: ${s.dir}/${x.file} should be numbered ${String(i + 1).padStart(2, '0')}`);
    });
    if (listed.length !== onDisk.length) fail(`src/styles/${s.dir}/ has ${onDisk.length} files; the manifest imports ${listed.length}`);
    if (new Set(listed.map((x) => x.file)).size !== listed.length) fail(`index.css imports a ${s.dir}/ file twice`);
  }
  for (const d of fs.readdirSync(STYLES, { withFileTypes: true })) {
    if (d.isDirectory() && !order.includes(d.name)) fail(`src/styles/${d.name}/ is not a sheet listed in port-edits.json`);
  }

  // No file over 300 lines.
  const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((d) => (d.isDirectory() ? walk(path.join(dir, d.name)) : [path.join(dir, d.name)]));
  for (const f of walk(STYLES).filter((x) => x.endsWith('.css'))) {
    const n = toLines(fs.readFileSync(f, 'utf8')).length;
    if (n > MAX_LINES) fail(`${path.relative(FRONTEND, f)} has ${n} lines (at most ${MAX_LINES})`);
  }

  // The manifest is imported once, from main.jsx, and nothing imports a sheet file on its own (no per-route sheets).
  const sheetDirs = new RegExp(`styles/(${order.map((d) => d.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})/|styles/index\\.css`);
  const fromMain = [];
  for (const f of walk(path.join(FRONTEND, 'src')).filter((x) => /\.(jsx?|css)$/.test(x) && !x.startsWith(STYLES))) {
    toLines(fs.readFileSync(f, 'utf8')).forEach((t, i) => {
      if (!/^\s*(import|@import)\b/.test(t) || !sheetDirs.test(t.replace(/\\/g, '/'))) return;
      if (path.relative(FRONTEND, f).replace(/\\/g, '/') === 'src/main.jsx' && /styles\/index\.css/.test(t)) fromMain.push(i + 1);
      else fail(`${path.relative(FRONTEND, f)}:${i + 1} imports a ported sheet itself; only main.jsx imports the manifest`);
    });
  }
  if (fromMain.length !== 1) fail(`src/main.jsx imports styles/index.css ${fromMain.length} times (once, please)`);

  // Each sheet: its files, joined, equal the old sheet minus the listed edits.
  const summary = [];
  const defined = new Set(data.setByMarkup);
  const uses = [];
  for (const s of data.sheets) {
    let oldText;
    try {
      oldText = execFileSync('git', ['-C', oldRepo, 'show', `${data.commit}:${s.path}`], { encoding: 'utf8', maxBuffer: 64 << 20 });
    } catch {
      fail(`cannot read ${s.path} at ${data.commit} from ${oldRepo} (pass --old <path>)`);
      continue;
    }
    const mine = data.edits.filter((e) => e.sheet === s.sheet);
    const { lines, problems } = expectedLines(oldText, s.mode, mine);
    problems.forEach((p) => fail(`${s.sheet}: ${p}`));
    const files = filesByDir.get(s.dir).map((x) => path.join(STYLES, s.dir, x.file));
    for (const d of compare(lines, files)) {
      fail(`${s.sheet}: ${path.relative(FRONTEND, d.file)}:${d.line} differs from old line ${d.old ?? '(inserted)'}\n      got:  ${d.got}\n      want: ${d.want}`);
    }
    for (const f of files) {
      // comments may name a token (commissions.css says never to use var(--accent)); blank them, keeping lines
      const css = fs.readFileSync(f, 'utf8').replace(/\/\*[\s\S]*?\*\//g, (c) => c.replace(/[^\n]/g, ' '));
      toLines(css).forEach((t, i) => {
        for (const m of t.matchAll(/(--[\w-]+)\s*:/g)) defined.add(m[1]);
        for (const m of t.matchAll(/var\(\s*(--[\w-]+)/g)) uses.push({ name: m[1], where: `${path.relative(FRONTEND, f)}:${i + 1}` });
      });
    }
    const count = (k) => mine.filter((e) => e.kind === k).length;
    summary.push(`${s.sheet.padEnd(28)} ${s.mode.padEnd(6)} old ${String(toLines(oldText).length).padStart(5)}  ported ${String(lines.length).padStart(5)}  files ${String(files.length).padStart(2)}  edits: ${count('remove')} removed, ${count('keep')} kept, ${count('rewrite')} rewritten, ${count('insert')} inserted`);
  }
  // Every var() names a property the ported sheets (or the markup) define: an undefined token cannot come back.
  for (const u of uses) if (!defined.has(u.name)) fail(`${u.where} uses ${u.name}, which nothing defines`);

  console.log(`CSS port proof against ${data.commit} (${path.relative(process.cwd(), oldRepo) || oldRepo})`);
  summary.forEach((l) => console.log(`  ${l}`));
  if (failures.length) {
    console.error(`\n${failures.length} problem(s):`);
    failures.slice(0, 50).forEach((f) => console.error(`  ${f}`));
    process.exit(1);
  }
  console.log(`OK: ${data.sheets.length} sheets, ${imports.length} files, ${data.edits.length} listed edits.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main();
