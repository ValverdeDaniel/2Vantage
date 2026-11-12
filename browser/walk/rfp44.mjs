// Slice 44's "done when" (plan.md §13.9 row 44; K1–K29): on GD2's RFP tab the band comes from the one headcount, the
// cross-check names the intake, census and Advisor counts, and carrier picks save. Run with `--need s44` on a freshly
// seeded GD2 (`seed_golden GD2`); it leaves GD2 with an intake count, a census and RFP picks, so seed it again after.
//
// A person does everything on the RFP tab, except two facts that belong to other tabs and are landed through their
// own doors: intake's enrolled count (PATCH intake answers) and an 8-person census (upload, import, Apply), so the
// three answers to "how many are enrolled" can disagree.

async function api(page, base, method, url, options = {}) {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
  const response = await page.request.fetch(`${base}/api/${url}`, {
    method,
    ...options,
    headers: { 'X-CSRFToken': csrf, Referer: base },
  });
  if (!response.ok()) throw new Error(`${method} ${url} answered ${response.status()}: ${await response.text()}`);
  return response.status() === 204 ? null : response.json();
}

/** Eight enrolled employees on the current plan: 5 EE, 1 ES, 1 EC, 1 FAM (synthetic). */
function censusCsv(plan) {
  const head = ['Employee ID', 'Relationship', 'First Name', 'Last Name', 'Date of Birth', 'Gender', 'Zip Code',
    'Hours Per Week', 'Medical Plan', 'Medical Tier'];
  const tiers = ['EE', 'EE', 'EE', 'EE', 'EE', 'ES', 'EC', 'FAM'];
  const rows = tiers.map((tier, i) => {
    const n = i + 1;
    return [`W44-${n}`, 'Employee', `Walker${n}`, `Synthetic${n}`, `198${n}-0${n}-1${n}`, n % 2 ? 'F' : 'M', '33602',
      '40', plan, tier];
  });
  return [head, ...rows].map((row) => row.join(',')).join('\n');
}

// Do `act` and wait for the RFP write it makes.
async function saved(page, act) {
  const answer = page.waitForResponse(
    (response) => /\/rfp\/(done\/)?$/.test(new URL(response.url()).pathname) && response.request().method() !== 'GET',
  );
  await act();
  const response = await answer;
  if (!response.ok()) throw new Error(`the write answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

export const rfp44 = {
  title: "Slice 44: GD2's RFP tab — the band from the one headcount, the cross-check, carrier picks that save",
  deal: 'GD2',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec, base } = ctx;
    let dealId;
    const group = (name) => page.getByRole('group', { name, exact: true });
    const chip = (name, label) => group(name).getByRole('button', { name: new RegExp(`^${label}`) });
    const card = () => page.locator('[data-guide="carriers-request"]');
    const enrolled = spec.plans
      .filter((p) => p.line === 'medical' && p.role === 'current')
      .reduce((sum, p) => sum + Object.values(p.enrollment || {}).reduce((a, b) => a + b, 0), 0);
    await signIn(ctx);
    await openDeal(ctx);
    await step('RFP sits under "1 · Get to Market" and opens the tab with the client in its subtitle', async () => {
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      await page.getByRole('link', { name: 'RFP', exact: true }).click();
      await page.waitForURL(/\/deals\/\d+\/rfp$/);
      await page.getByText(`The request that goes out for ${spec.client}.`).waitFor({ timeout: 45000 });
      await page.getByText('✓ 0 of 3 completed').waitFor();
    });
    await step(`the band comes from the Advisor's ${enrolled} enrolled: small, through Warner Pacific`, async () => {
      await page.getByText(`Small group (2–50) · ${enrolled} enrolled`).waitFor();
      await page.getByText(`no census yet — the band's ${enrolled} enrolled come from the Advisor`).waitFor();
      const warner = chip('Send through', 'Warner Pacific');
      await warner.getByText('standard under 51').waitFor();
      if ((await warner.getAttribute('aria-pressed')) !== 'true') throw new Error('Warner Pacific is not the route');
    });
    await step('intake says 9 enrolled and an 8-person census lands: the cross-check names all three', async () => {
      await api(page, base, 'PATCH', `deals/${dealId}/intake/`, { data: { answers: { enrolled_count: '9' } } });
      const plan = spec.plans.find((p) => p.line === 'medical' && p.role === 'current').name;
      const document = await api(page, base, 'POST', `deals/${dealId}/documents/`, {
        multipart: {
          file: { name: 'Walk 44 census (synthetic).csv', mimeType: 'text/csv', buffer: Buffer.from(censusCsv(plan)) },
          kind: 'census',
          lines: '[]',
        },
      });
      const proposed = await api(page, base, 'POST', `deals/${dealId}/census/imports/`, { data: { document_id: document.id } });
      await api(page, base, 'POST', `census/imports/${proposed.id}/apply/`);
      await page.reload();
      await page.getByText(/of 3 completed/).waitFor({ timeout: 45000 });
      await page.getByText(/⚠ Enrolled: intake 9 · census 8 · Advisor \d+ — the band uses the Advisor, \d+\./).waitFor();
      await page.getByText(/Census · 8 employees · 0 dependents · \d+% ready/).waitFor();
    });
    await step('Florida Blue, Cigna and a dimmed Guardian are picked, and the summary counts three', async () => {
      const guardian = chip('Ancillary carriers', 'Guardian');
      if (!/None of the lines you picked/.test((await guardian.getAttribute('title')) || '')) {
        throw new Error('Guardian should say it quotes none of the lines picked');
      }
      await saved(page, () => chip('Medical carriers', 'Florida Blue').click());
      await saved(page, () => chip('Medical carriers', 'Cigna').click());
      await saved(page, () => guardian.click());
      await card().getByText('Through Warner Pacific · 3 carriers').waitFor();
    });
    await step('the picks save: after a reload the three chips are still on, and a second click takes one off', async () => {
      await page.reload();
      await page.getByText(/of 3 completed/).waitFor({ timeout: 45000 });
      for (const [name, label] of [['Medical carriers', 'Florida Blue'], ['Medical carriers', 'Cigna'],
        ['Ancillary carriers', 'Guardian']]) {
        await chip(name, label).and(page.locator('[aria-pressed="true"]')).waitFor();
      }
      await saved(page, () => chip('Ancillary carriers', 'Guardian').click());
      await page.reload();
      await page.getByText(/of 3 completed/).waitFor({ timeout: 45000 });
      await card().getByText('Through Warner Pacific · 2 carriers').waitFor();
    });
    await step('Mark completed puts the card away; a pick inside it takes the mark off', async () => {
      await saved(page, () => card().getByRole('button', { name: '✓ Mark completed' }).click());
      await page.getByText('✓ 1 of 3 completed').waitFor();
      await card().getByRole('button', { name: /^Expand / }).click();
      await saved(page, () => chip('Medical carriers', 'Aetna').click());
      await page.getByText('✓ 0 of 3 completed').waitFor();
      await card().getByRole('button', { name: '✓ Mark completed' }).waitFor();
    });
    await step('Direct to carriers overrides the band; Warner Pacific again follows it; no funding says so', async () => {
      await saved(page, () => chip('Send through', 'Direct to carriers').click());
      await card().getByText('Direct to carriers · 3 carriers').waitFor();
      await saved(page, () => chip('Send through', 'Warner Pacific').click());
      await card().getByText('Through Warner Pacific · 3 carriers').waitFor();
      for (const label of ['Fully insured', 'Level funded']) {
        const funding = chip('Funding to quote', label);
        if ((await funding.getAttribute('aria-pressed')) === 'true') await saved(page, () => funding.click());
      }
      await page.getByText('Pick at least one funding type').waitFor();
      await page.reload();
      await page.getByText(/of 3 completed/).waitFor({ timeout: 45000 });
      await page.getByText('Pick at least one funding type').waitFor();
    });
  },
};
