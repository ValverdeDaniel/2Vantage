// Slice 52's "done when" (plan.md §13.10 row 52; D113, G99, G102, G109): a synthetic filled Florida Blue 51+ form,
// dropped in Work with Claude on the Questionnaire tab, is read and staged — nothing on the form changes; once the
// form is signed the staged read cannot be used (the card says so, Use is off, the apply door answers 409); reopened,
// "Use this scan ▸" puts the answers on the form as Claude's reads.
//
// Run it with `--need s52` as an admin (golden-admin). Each run makes one prospect, "Walk52 Filled form (synthetic)",
// archived at the end, and ONE REAL Claude read (Sonnet 5.5, a few cents of the build's $20 cap, `manage.py
// ai_spend`); the backend needs ANTHROPIC_API_KEY, the PHI-gate switch on (AI_PHI_READERS, the dev stack's) and the
// worker running. The filled form is `manage.py questionnaire_sample`'s (G109): the questionnaire's own blank stamped
// with invented answers, made here through docker compose when WALK52_FILE does not name one. No real client's file.

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

import { OUT, REPO } from '../shared/config.mjs';

const READ_MS = 300000;
const NAME = 'Walk52 Filled form (synthetic)';
const FORM = 'fl_blue_51';

function sampleFile() {
  const named = process.env.WALK52_FILE;
  if (named) return named;
  const dir = path.join(OUT, 's52-sample');
  const file = path.join(dir, `${FORM}-filled-synthetic.pdf`);
  if (!fs.existsSync(file)) {
    fs.mkdirSync(dir, { recursive: true });
    const run = (args) => execFileSync('docker', ['compose', ...args], { cwd: REPO, stdio: 'pipe' });
    run(['exec', '-T', 'backend', 'python', 'manage.py', 'questionnaire_sample', '--out', '/tmp/walk52']);
    run(['cp', 'backend:/tmp/walk52/.', dir]);
  }
  return file;
}

async function dropPdf(page, name, b64) {
  await page.evaluate(
    ({ name, b64 }) => {
      const transfer = new DataTransfer();
      transfer.items.add(new File([Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))], name, { type: 'application/pdf' }));
      const target = document.querySelector('[data-claude-panel]');
      ['dragenter', 'dragover', 'drop'].forEach((type) =>
        target.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: transfer })),
      );
    },
    { name, b64 },
  );
}

// An API call from the page; once more after a moment when the dev server was reloading (another lane's edit).
function api(page, base) {
  const once = (method, url, body) =>
    page.evaluate(
      async ({ base, method, url, body }) => {
        const token = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
        const res = await fetch(`${base}/api/${url}`, {
          method,
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
          body: body ? JSON.stringify(body) : undefined,
        });
        return { status: res.status, body: await res.json().catch(() => null) };
      },
      { base, method, url, body },
    );
  return async (method, url, body) => {
    const answer = await once(method, url, body);
    if (answer.body !== null || method !== 'GET') return answer;
    await page.waitForTimeout(3000);
    return once(method, url, body);
  };
}

export const questionnaireRead52 = {
  title: 'Claude reads a filled questionnaire: staged, refused while the form is signed, used once reopened',
  deal: 'GD6',
  async run(ctx, { signIn }) {
    const { page, step, base } = ctx;
    const call = api(page, base);
    const drawer = page.getByRole('dialog', { name: 'Work with Claude' });
    const openDrawer = async () => {
      await page.getByRole('button', { name: 'Work with Claude' }).click();
      await drawer.getByText('Review this scan').waitFor();
    };
    let dealId;
    let jobId;
    await signIn(ctx);
    await step('＋ New deal makes a prospect, and its checklist picks Florida Blue 51+', async () => {
      await page.getByRole('button', { name: /New deal/ }).click();
      await page.waitForURL(/\/deals\/new/);
      await page.getByLabel('Group name *').fill(NAME);
      await page.getByRole('button', { name: /Create deal & open intake/ }).click();
      await page.waitForURL(/\/deals\/\d+\/intake/, { timeout: 30000 });
      dealId = page.url().match(/\/deals\/(\d+)/)[1];
      const picked = await call('PATCH', `deals/${dealId}/questionnaires/choice/`, {
        item: 'medical_questionnaire',
        choice: FORM,
      });
      if (picked.status !== 200) throw new Error(`choice answered ${picked.status}`);
    });
    await step('the Questionnaire tab shows the form, and Work with Claude opens over it', async () => {
      await page.goto(`${base}/deals/${dealId}/questionnaire`);
      await page.getByText('Florida Blue Underwriting Questionnaire').first().waitFor();
      await page.getByRole('button', { name: 'Work with Claude' }).click();
      await drawer.waitFor();
    });
    await step('the filled form dropped there is read and staged: "Review this scan" (D113, G99)', async () => {
      const b64 = fs.readFileSync(sampleFile()).toString('base64');
      await dropPdf(page, 'filled-questionnaire.pdf', b64);
      await drawer.getByText('Review this scan').waitFor({ timeout: READ_MS });
      await drawer.getByText('1. Name of Business').waitFor();
      await drawer.getByText('Example Trial Fabrication LLC').first().waitFor();
      await drawer.getByText(/Group Medical Conditions 1 → a new row/).waitFor();
      jobId = (await call('GET', `deals/${dealId}/ai/`)).body.waiting[0].job_id;
    });
    await step('nothing on the form changed while it waits', async () => {
      const form = await call('GET', `deals/${dealId}/questionnaires/${FORM}/`);
      if (form.body.started) throw new Error('the form was written before anyone used the read');
    });
    await step('signed, the form takes nothing: the card says so, Use is off, the door answers 409 (G99)', async () => {
      const signed = await call('POST', `deals/${dealId}/questionnaires/${FORM}/sign/`, {
        who: 'officer',
        name: 'Riley Example',
        authorized: true,
        sign_anyway: true,
      });
      if (signed.status !== 200) throw new Error(`sign answered ${signed.status}`);
      await page.reload();
      await openDrawer();
      await drawer.getByText(/Florida Blue 51\+ is signed, so nothing from this read can be used/).waitFor();
      if (!(await drawer.getByRole('button', { name: 'Use this scan ▸' }).isDisabled())) throw new Error('Use is on');
      const refused = await call('POST', `ai/jobs/${jobId}/apply/`, {});
      if (refused.status !== 409 || !/is signed/.test(refused.body?.detail)) throw new Error(`apply ${refused.status}`);
    });
    await step('reopened, "Use this scan ▸" puts the answers on the form as Claude’s reads', async () => {
      const reopened = await call('POST', `deals/${dealId}/questionnaires/${FORM}/reopen/`, { reason: 'Walk52' });
      if (reopened.status !== 200) throw new Error(`reopen answered ${reopened.status}`);
      await page.reload();
      await openDrawer();
      await drawer.getByRole('button', { name: 'Use this scan ▸' }).click();
      await page.getByText(/Scan applied — Florida Blue 51\+/).first().waitFor({ timeout: 30000 });
      const form = await call('GET', `deals/${dealId}/questionnaires/${FORM}/`);
      if (form.body.values.txtCoName !== 'Example Trial Fabrication LLC') throw new Error('Name of Business not read');
      if (form.body.sources.txtCoName?.origin !== 'ai') throw new Error('the answer is not Claude’s read');
    });
    if (dealId) {
      // tidy: archive the walk's prospect (slice 38's archive; best effort)
      const deal = await call('GET', `deals/${dealId}/`);
      if (deal.body?.client?.id) await call('POST', `clients/${deal.body.client.id}/archive/`, { archived: true });
    }
  },
};
