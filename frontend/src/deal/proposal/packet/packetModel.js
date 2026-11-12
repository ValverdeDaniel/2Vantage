// The packet card's pure rules (plan.md §8.15; J96, J101, J103; the old ProposalPacketCard.jsx at 891f1b3): which
// files are ticked for the zip (a download preference kept in this browser under the old key, never on the deal), the
// card's summary, the next version's number, and what one issued version says. The files and their words come from
// /api/meta/ `proposal.issue`; every state and sentence is the server's.
import { formatDateTime, personName } from '../../../lib/format';

export const PREFS_KEY = 'vantage.bnf.proposalPacket';
const LEVELS = { stop: 'Stops', warn: 'Check', info: 'Note' };

export function levelWord(level) {
  return LEVELS[level] ?? 'Check';
}

export function loadPrefs(storage = globalThis.localStorage) {
  try {
    return JSON.parse(storage?.getItem(PREFS_KEY) ?? 'null') || {};
  } catch {
    return {};
  }
}

export function savePrefs(prefs, storage = globalThis.localStorage) {
  try {
    storage?.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    // A browser refusing storage only loses the memory of the choice.
  }
}

/** The keys ticked for the zip, in the card's order: every file unless unticked. */
export function ticked(files, ticks = {}) {
  return files.filter((file) => ticks[file.key] !== false).map((file) => file.key);
}

/** "3 of 3 ticked · ⚠ 2 to check" (the old summary). */
export function summaryWords(count, total, checks) {
  const files = `${count} of ${total} ticked`;
  if (!checks) return files;
  return `${files} · ${checks.length ? `⚠ ${checks.length} to check` : '✓ Nothing to fix'}`;
}

/** The number the next Issue makes: one past the highest version, failed ones included (never reused). */
export function nextVersion(issues = []) {
  return issues.reduce((top, issue) => Math.max(top, issue.version), 0) + 1;
}

export function latestIssued(issues = []) {
  return issues.find((issue) => issue.state === 'issued') ?? null;
}

export function buildingIssue(issues = []) {
  return issues.find((issue) => issue.state === 'building') ?? null;
}

/** One version's line in the Issued list. `job` is the live job from the AI poll, when it is still running. */
export function issueWords(issue, job) {
  if (issue.state === 'issued') {
    const by = issue.issued_by ? ` by ${personName(issue.issued_by, '')}` : '';
    return `Issued ${formatDateTime(issue.issued_at)}${by}`;
  }
  if (issue.state === 'building') {
    const live = job ?? issue.job;
    const step = live?.step && live.step !== 'Waiting to start' ? ` — ${live.step}` : '';
    return live?.status === 'queued' ? 'Waiting to start building the files' : `Building the files · ${live?.progress ?? 0}%${step}`;
  }
  return `Could not be built: ${issue.error}`;
}

/** Why "Issue to client" waits, or '': a version still building, or a write still saving (J101). A proposal that
 *  is not ready still lets the click through: the server answers with its sentence, as the done-when asks. */
export function issueBlocked({ building, saving }) {
  if (building) return `Proposal v${building.version} is still being built.`;
  if (saving) return 'Saving your changes first…';
  return '';
}
