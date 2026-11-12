// Slice 49's "done when" (plan.md §13.10 row 49; H25–H58, H120, OQ101): on a fresh GD1 at 5 % on Medical, Mark sold
// on CG1N opens the booking summary; selling U2 too books both plans (one record per carrier, OQ75) and the client is a
// New client; the Commission tab shows the booked block and the frozen shares; /commissions lists both records; then
// un-selling both plans voids both records and returns the client to Prospect. Run with `--need s49`.
//
// It writes to GD1 (the rate, two sales, two un-sales): re-seed GD1 after (`seed_golden GD1`).

const SOLD = [
  { carrier: 'Cigna', name: 'LocalPlus HDHP 3000 — negotiated', expected: '$10,454' },
  { carrier: 'UnitedHealthcare', name: 'Choice Plus 1500', expected: '$10,036' },
];

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

async function planAction(page, plan, action) {
  await page.getByRole('button', { name: `Actions for ${plan.carrier} — ${plan.name}` }).first().click();
  await page.getByRole('menuitem', { name: action }).click();
}

export const booking49 = {
  title: 'GD1 sold: Mark sold opens the booking summary; two plans book two records; un-selling voids them',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base } = ctx;
    let dealId;
    let clientId;
    await signIn(ctx);
    await openDeal(ctx);

    await step('GD1 is a Prospect with nothing booked; Medical is agreed at 5 %', async () => {
      dealId = page.url().match(/\/deals\/(\d+)/)[1];
      const header = await api(page, base, `deals/${dealId}/`);
      clientId = header.client.id;
      if (header.client.relationship !== 'prospect') throw new Error(header.client.relationship);
      const tab = await api(page, base, `deals/${dealId}/commission/`, 'PATCH', { rates: { medical: '5' } });
      if (tab.booking.state !== 'none') throw new Error(`booking ${tab.booking.state}`);
    });

    await step(`Mark sold on ${SOLD[0].carrier} ${SOLD[0].name} opens the booking summary with its record`, async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: /^Medical/ }).click();
      await planAction(page, SOLD[0], 'Mark sold');
      const modal = page.getByRole('dialog', { name: /^Booked — Golden Manufacturing/ });
      await modal.waitFor();
      await modal.getByRole('cell', { name: SOLD[0].carrier, exact: true }).waitFor();
      await modal.getByText(SOLD[0].expected).first().waitFor();
      await modal.getByText('Who gets what', { exact: true }).waitFor();
      await modal.getByRole('button', { name: 'Done' }).click();
      await modal.waitFor({ state: 'detached' });
    });

    await step(`selling ${SOLD[1].carrier} too books it without reopening the summary; the client is a New client`, async () => {
      await planAction(page, SOLD[1], 'Mark sold');
      await page.getByText(`${SOLD[1].name} marked sold`).waitFor();
      if (await page.getByRole('dialog', { name: /^Booked —/ }).count()) throw new Error('the summary reopened');
      const tab = await api(page, base, `deals/${dealId}/commission/`);
      const carriers = tab.booking.records.map((row) => row.carrier).sort();
      if (carriers.join('|') !== 'Cigna|UnitedHealthcare') throw new Error(carriers.join(', '));
      const header = await api(page, base, `deals/${dealId}/`);
      if (header.client.relationship !== 'new_client') throw new Error(header.client.relationship);
    });

    await step('the Commission tab shows the booked block ($20,490) and the frozen shares; Booked · view reopens it', async () => {
      await page.getByRole('link', { name: 'Commission', exact: true }).click();
      await page.getByText('Booked at sale (2 lines)').waitFor();
      await page.getByText('$20,490').first().waitFor();
      await page.getByText('booked — splits frozen').waitFor();
      await page.getByRole('button', { name: 'Booked · view' }).click();
      const modal = page.getByRole('dialog', { name: /^Booked —/ });
      await modal.getByRole('cell', { name: SOLD[1].carrier, exact: true }).waitFor();
      await modal.getByRole('button', { name: 'Done' }).click();
    });

    await step('/commissions lists both records on the Book, with the deal filter from Open in Commissions', async () => {
      await page.goto(`${base}/commissions?deal=${dealId}`);
      await page.getByRole('heading', { name: 'Commissions' }).waitFor();
      await page.getByRole('cell', { name: 'Cigna', exact: true }).waitFor();
      await page.getByRole('cell', { name: 'UnitedHealthcare', exact: true }).waitFor();
      await page.getByText('Clear deal filter').waitFor();
    });

    await step('un-selling both plans voids both records and returns the client to Prospect', async () => {
      await page.goto(`${base}/deals/${dealId}/advisor`);
      await page.getByRole('button', { name: /^Medical/ }).click();
      for (const plan of SOLD) {
        await planAction(page, plan, 'Un-sell');
        await page.getByText(`${plan.name} un-sold`).waitFor();
      }
      const book = await api(page, base, `commissions/records/?deal=${dealId}&status=void`);
      if (book.rows.length !== 2) throw new Error(`${book.rows.length} void records`);
      const client = await api(page, base, `clients/${clientId}/`);
      if (client.relationship !== 'prospect') throw new Error(client.relationship);
      const tab = await api(page, base, `deals/${dealId}/commission/`);
      if (tab.booking.state !== 'none') throw new Error(`booking ${tab.booking.state}`);
    });
  },
};
