// Slice 48's "done when" (plan.md §13.10 row 48; H1–H24, H95–H101, H109/K29): a 60/40 split previews and saves. On
// GD1's Commission tab: a 5 % agreed rate on Medical is worth 5 % of its renewal; a second producer at 40 % of the pool
// leaves the primary 60 %, which the live preview shows before Save; Save for this deal keeps it after a reload. The
// RFP prints the agreed rate with "Commission ▸"; /commissions lists the producer. Run with `--need s48`.
//
// It writes to GD1 (the rate, the split and its owner) and adds one synthetic producer Party, "Walk 48 Producer
// (synthetic)", the first time: re-seed GD1 after (`seed_golden GD1`).

const SECOND = 'Walk 48 Producer (synthetic)';

async function api(page, base, url, method = 'GET', body = undefined) {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
  const response = await page.request.fetch(`${base}/api/${url}`, {
    method,
    headers: { 'X-CSRFToken': csrf, Referer: base, 'Content-Type': 'application/json' },
    data: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok()) throw new Error(`${method} ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

export const commission48 = {
  title: "GD1's Commission tab: an agreed rate, then a 60/40 split of the producer pool previews and saves",
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base } = ctx;
    let dealId;
    await signIn(ctx);

    await step(`"${SECOND}" is on Producers & partners (added through the form the first time)`, async () => {
      const roster = await api(page, base, 'commissions/parties/');
      await page.goto(`${base}/commissions`);
      await page.getByRole('heading', { name: 'Commissions' }).waitFor();
      if (!roster.producers.some((row) => row.name === SECOND)) {
        await page.getByRole('button', { name: '＋ Add external broker / partner' }).click();
        await page.getByLabel('Kind').selectOption('producer');
        await page.getByLabel('Name').fill(SECOND);
        await page.getByLabel('appointed & licensed').check();
        await page.getByRole('button', { name: 'Add', exact: true }).click();
      }
      await page.getByRole('cell', { name: SECOND, exact: true }).waitFor();
      await page.getByRole('tab', { name: 'Settings' }).waitFor();
    });

    await step('Commission sits in the sidebar under 1 · Get to Market and opens the tab', async () => {
      await page.goto(`${base}/`);
      await openDeal(ctx);
      dealId = page.url().match(/\/deals\/(\d+)/)[1];
      await page.getByRole('link', { name: 'Commission', exact: true }).click();
      await page.getByText('Commission per line').waitFor();
      await page.getByText('Producers & splits').first().waitFor();
    });

    await step('a 5 % agreed rate on Medical is worth 5 % of the renewal: $29,886 a year', async () => {
      const rate = page.getByLabel('Medical agreed rate');
      await rate.fill('5');
      await rate.press('Enter');
      await page.getByText('$29,886').first().waitFor();
      await page.getByText(/\$597,720\/yr premium · Renewal · 3 plans/).waitFor();
    });

    await step('the primary and a 40 % secondary producer preview 24.0 % and 16.0 % (60/40 of the 40 % pool)', async () => {
      await page.getByLabel('Primary producer').selectOption({ label: 'Golden Admin' });
      await page.getByRole('button', { name: '＋ Secondary producer' }).click();
      await page.getByLabel('Person', { exact: true }).selectOption({ label: SECOND });
      const amount = page.getByLabel('Split amount');
      await amount.fill('40');
      await amount.press('Enter');
      await page.getByText('24.0% · $7,173').waitFor();
      await page.getByText('16.0% · $4,782').waitFor();
      await page.getByText(/House\s*60\.0%/).waitFor();
    });

    await step('Save for this deal keeps the split, and a reload still shows it', async () => {
      await page.getByLabel('Applies to').selectOption('deal');
      await page.getByRole('button', { name: 'Save for this deal' }).click();
      await page.getByText('set on this deal').waitFor();
      await page.reload();
      await page.getByText('set on this deal').waitFor();
      await page.getByText('16.0% · $4,782').waitFor();
      const saved = await api(page, base, `deals/${dealId}/commission/`);
      const roles = saved.split.rows.map((row) => `${row.role}:${row.name}`);
      if (roles.join('|') !== `primary:Golden Admin|secondary:${SECOND}`) throw new Error(roles.join(', '));
    });

    await step('the RFP prints the agreed rate, with "Commission ▸" back to the tab (K29)', async () => {
      await page.getByRole('link', { name: 'RFP', exact: true }).click();
      await page.getByText(/5% — the agreed rates, printed on the request form/).waitFor();
      await page.getByRole('link', { name: 'Commission ▸' }).click();
      await page.waitForURL(/\/commission$/);
      await page.getByText('Commission per line').waitFor();
    });
  },
};
