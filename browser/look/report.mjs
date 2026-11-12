// The Look lane's report (Q.5): every screen state judged as match, intended (labelled in accepted.json),
// pending (2Vantage's screen not built yet) or unexplained. Written outside the repository.

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

export function loadAccepted(file = path.join(HERE, 'accepted.json')) {
  return JSON.parse(fs.readFileSync(file, 'utf8')).accepted || [];
}

const sha256 = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

// An unlabelled failing check is unexplained; a label whose image changed since signing no longer applies.
export function judge(row, accepted) {
  if (row.pending) return 'pending';
  if (row.error) return 'error';
  const failing = ['pixels', 'classes', 'style'].filter((check) => row[check] && !row[check].same);
  if (!failing.length) return 'match';
  const newHash = row.new?.file && fs.existsSync(row.new.file) ? sha256(row.new.file) : null;
  const labelled = failing.every((check) => accepted.some((label) => label.screen === row.key
    && (label.width == null || label.width === row.width) && label.check === check
    && label.signed_by && (!label.new_sha256 || label.new_sha256 === newHash)));
  return labelled ? 'intended' : 'unexplained';
}

function line(row) {
  if (row.pending) return `| ${row.key} | ${row.width} | pending slice ${row.pending} | — | — | — | ${row.old?.hidden?.join(' ') || ''} |`;
  if (row.error) return `| ${row.key} | ${row.width} | error | — | — | — | ${row.error} |`;
  const pct = (row.pixels.ratio * 100).toFixed(2);
  const cls = row.classes.same ? 'same' : `${row.classes.old_count} → ${row.classes.new_count}`;
  const sty = row.style.same ? 'same' : `${Object.values(row.style.selectors).filter((v) => v !== 'same' && v !== 'in neither').length} differ`;
  return `| ${row.key} | ${row.width} | ${row.verdict} | ${pct}% | ${cls} | ${sty} | ${row.old?.hidden?.join(' ') || ''} |`;
}

export function write(dir, rows, meta) {
  fs.writeFileSync(path.join(dir, 'report.json'), JSON.stringify({ ...meta, rows }, null, 1));
  const counts = rows.reduce((acc, row) => ({ ...acc, [row.verdict]: (acc[row.verdict] || 0) + 1 }), {});
  const md = [
    `# Look lane — ${meta.started}`,
    '',
    `Old ${meta.old} · new ${meta.new} · clock ${meta.clock} · ${Object.entries(counts).map(([k, v]) => `${v} ${k}`).join(', ')}`,
    '',
    '| Screen | Width | Verdict | Pixels differ | bnf/bb/gk/rr classes (old → new) | Key styles | Hidden on old |',
    '|---|---|---|---|---|---|---|',
    ...rows.map(line),
    '',
    'Captures, diffs and report.json sit beside this file. Pixels "same" means at most 0.02% of pixels differ.',
  ].join('\n');
  fs.writeFileSync(path.join(dir, 'report.md'), `${md}\n`);
  return counts;
}
