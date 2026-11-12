// Slice 32's "done when" (plan.md §13.8 row 32; need 12; J70, J96–J104): on GD1's Proposal tab, the packet card over
// the board in presented mode; an uncovered shopped line is refused with its sentence; Issue makes v1 with three
// stored, protected files and moves the deal to Proposal; v2 leaves v1's bytes unchanged. Run with `--need s32` on a
// freshly seeded GD1 (it starts at v1). It issues two versions and leaves them: re-seed GD1 after
// (`manage.py seed_golden`). Its two set-up writes (Vision's pick taken off and put back, a title) go through the API,
// as the builder would make them.

import crypto from 'node:crypto';

async function call(page, base, url, method = 'GET', body = undefined) {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
  return page.request.fetch(`${base}/api/${url}`, {
    method,
    headers: { 'X-CSRFToken': csrf, Referer: base, 'Content-Type': 'application/json' },
    data: body ? JSON.stringify(body) : undefined,
  });
}

async function api(page, base, url, method, body) {
  const response = await call(page, base, url, method, body);
  if (!response.ok()) throw new Error(`${method || 'GET'} ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

async function digests(page, base, dealId, version) {
  const out = {};
  for (const file of ['pdf', 'pptx', 'xlsx']) {
    const response = await call(page, base, `deals/${dealId}/proposal/issues/${version}/${file}/`);
    if (!response.ok()) throw new Error(`v${version} ${file}: ${response.status()}`);
    out[file] = crypto.createHash('sha256').update(await response.body()).digest('hex');
  }
  return out;
}

const SENTENCE =
  'A proposal always carries our recommendation. Pick a recommended plan before this goes to the client: Vision.';

export const issue32 = {
  title: "GD1's Proposal tab: the packet card over the presented board; refusal, Issue v1 and v2 with v1's bytes kept",
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base, spec } = ctx;
    let dealId;
    let vision;
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Proposal tab shows "Plan comparison", the Proposal packet and "Issue to client (v1)"', async () => {
      dealId = page.url().match(/\/deals\/(\d+)/)[1];
      await page.getByRole('link', { name: 'Proposal', exact: true }).click();
      await page.waitForURL(/\/deals\/\d+\/proposal/);
      await page.getByText('Plan comparison', { exact: true }).waitFor();
      await page.getByText('Proposal packet', { exact: true }).waitFor();
      await page.getByRole('button', { name: 'Issue to client (v1)' }).waitFor();
      await page.getByRole('button', { name: 'Expand Proposal packet' }).click(); // it starts closed, as the old one
      await page.getByText('In the zip', { exact: true }).waitFor();
    });
    await step('under it, the board in presented mode: the legend, the line tabs and the current medical plans', async () => {
      await page.getByText('Needs checking', { exact: true }).waitFor();
      await page.getByRole('navigation', { name: 'Lines of coverage' }).waitFor();
      const current = spec.plans.find((plan) => plan.line === 'medical' && plan.role === 'current');
      await page.getByText(current.name, { exact: false }).filter({ visible: true }).first().waitFor();
    });
    await step('with Vision left without a pick, Issue is refused with its sentence and nothing is issued', async () => {
      const body = await api(page, base, `deals/${dealId}/proposal/`);
      vision = body.lines.find((line) => line.line === 'vision').recommendation.plans[0].plan_id;
      await api(page, base, `plans/${vision}/recommend/`, 'POST', { recommended: false });
      await page.reload();
      await page.getByRole('button', { name: 'Issue to client (v1)' }).click();
      await page.getByText(SENTENCE, { exact: true }).nth(1).waitFor(); // the card's banner, then the refusal's toast
      const issues = await api(page, base, `deals/${dealId}/proposal/issues/`);
      if (issues.length) throw new Error(`${issues.length} versions made`);
      await api(page, base, `plans/${vision}/recommend/`, 'POST', { recommended: true });
    });
    let first;
    await step('Issue to client makes v1: the worker builds it and the Issued list shows it with its files', async () => {
      await page.reload();
      await page.getByRole('button', { name: 'Issue to client (v1)' }).click();
      const row = page.locator('[data-issue="issued"]').filter({ hasText: 'Proposal v1' });
      await row.waitFor({ timeout: 90000 });
      await row.getByRole('button', { name: '⬇ Client PDF' }).waitFor();
    });
    await step('v1 is three protected Documents of kind proposal, and the deal is at the Proposal stage', async () => {
      const docs = await api(page, base, `deals/${dealId}/documents/`);
      const issued = docs.filter((doc) => doc.kind === 'proposal' && doc.label.startsWith('Proposal v1 · '));
      if (issued.length !== 3 || !issued.every((doc) => doc.protected)) throw new Error(JSON.stringify(issued));
      const { stage } = await api(page, base, `deals/${dealId}/`);
      if (stage !== 'proposal') throw new Error(`stage ${stage}`);
      first = await digests(page, base, dealId, 1);
    });
    await step("v1's PDF downloads from the Issued list under its name, without -DRAFT", async () => {
      const row = page.locator('[data-issue="issued"]').filter({ hasText: 'Proposal v1' });
      const download = page.waitForEvent('download', { timeout: 60000 });
      await row.getByRole('button', { name: '⬇ Client PDF' }).click();
      const name = (await download).suggestedFilename();
      if (!name.endsWith('Benefits Proposal.pdf')) throw new Error(name);
    });
    await step("after a change, Issue makes v2, and v1's stored bytes are unchanged", async () => {
      await api(page, base, `deals/${dealId}/proposal/`, 'PATCH', { title: 'Walk title (synthetic)' });
      await page.reload();
      await page.getByRole('button', { name: 'Issue to client (v2)' }).click();
      await page.locator('[data-issue="issued"]').filter({ hasText: 'Proposal v2' }).waitFor({ timeout: 90000 });
      const again = await digests(page, base, dealId, 1);
      if (JSON.stringify(again) !== JSON.stringify(first)) throw new Error('v1 changed');
      const second = await digests(page, base, dealId, 2);
      if (second.pdf === first.pdf) throw new Error('v2 is v1');
      await api(page, base, `deals/${dealId}/proposal/`, 'PATCH', { title: '' });
    });
  },
};
