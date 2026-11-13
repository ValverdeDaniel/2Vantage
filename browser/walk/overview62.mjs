// Slice 62's "done when" (plan.md §13.10 row 62; §13.2 row 62; M1–M38, M112, CL4, CL26; OQ96, OQ101): deals open on
// the Overview; its blocks stand in the old Overview's order, with the Waiting banner under the title (OQ96's
// default): title row, banner, header (identity, chips, client box, facts), tiles; a prospect's box offers Convert to
// client, refused while the deal is lost; a converted client's box links to the client (the client dialog until 67);
// a fact typed in the header lands in intake; GD1-sold's box is a link and its Expected revenue its key's $20,491.
// Run with `--need s62` on a fresh GD2 (`manage.py seed_golden GD2`); it marks GD2 lost, reopens and converts it and
// types a FEIN, so seed GD2 again afterwards. GD1-sold is only read.

const LOST_SENTENCE = 'This deal is marked lost — reopen it before converting the client.';
const SOLD_CLIENT = 'Golden Manufacturing Sold (synthetic)';

async function api(page, base, url) {
  const response = await page.request.fetch(`${base}/api/${url}`);
  if (!response.ok()) throw new Error(`GET ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

// The tab's own region, so the header strip above every tab (M112) is never mistaken for the Overview's header.
const tab = (page) => page.getByRole('region', { name: 'Overview' });
const top = async (locator) => (await locator.first().boundingBox()).y;

export const overview62 = {
  title: 'Slice 62: deals open on the Overview; its blocks in the old order (Waiting banner under the title, OQ96); the client box',
  deal: 'GD2',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec, base } = ctx;
    let dealId;
    await signIn(ctx);
    await openDeal(ctx);

    await step('the deal opens on the Overview (O.4; plan.md §8.1)', async () => {
      await page.waitForURL(/\/deals\/\d+\/overview/);
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      await tab(page).getByText(/^Who this client is, where the deal stands/).waitFor();
      const header = await api(page, base, `deals/${dealId}/`);
      if (header.client.relationship !== 'prospect') throw new Error('GD2 is not a prospect: run seed_golden GD2 first');
    });

    await step('the blocks stand in the old order: title row, Waiting banner (OQ96), header and facts, tiles', async () => {
      const region = tab(page);
      const order = [
        ['title row', region.getByText(/^Who this client is, where the deal stands/)],
        ['Waiting banner', region.getByText(/^Waiting on|^Status/)],
        ['header', region.getByText(spec.client, { exact: true })],
        ['client box', region.getByText('Not on the client book yet')],
        ['facts', region.getByText('Legal name', { exact: true })],
        ['tiles', region.getByText('Intake complete', { exact: true })],
      ];
      let last = -1;
      for (const [name, locator] of order) {
        const y = await top(locator);
        if (y < last) throw new Error(`${name} stands above the block before it`);
        last = name === 'client box' ? last : y; // the client box sits beside the name, on the same row
      }
      // the tiles' own labels: the Activity card's outreach strip says "Last contact" too (slice 63)
      for (const label of ['Plans quoted', 'Last contact', 'Expected revenue']) await region.locator('.bb-metric-row').getByText(label, { exact: true }).waitFor();
      await region.getByText('New business', { exact: true }).waitFor();
      await region.getByText(/^Open \d+ days?$/).waitFor();
    });

    await step('the tiles are the read’s: Plans quoted counts GD2’s quotes (M36)', async () => {
      const read = await api(page, base, `deals/${dealId}/overview/`);
      const quotes = spec.plans.filter((plan) => plan.role !== 'current').length;
      if (read.tiles.plans_quoted !== quotes) throw new Error(`plans quoted ${read.tiles.plans_quoted}, spec ${quotes}`);
      const card = tab(page).locator('.bb-stat-card', { hasText: 'Plans quoted' });
      await card.getByText(String(quotes), { exact: true }).waitFor();
    });

    await step('Mark as lost… opens the inline row; Confirm lost shows the lost banner and hides the Waiting banner (M2, M4, M34)', async () => {
      await tab(page).getByRole('button', { name: 'Mark as lost…' }).click();
      await tab(page).getByRole('textbox', { name: 'Why did we lose it? (optional)' }).fill('Walk 62 (synthetic)');
      await tab(page).getByRole('button', { name: 'Confirm lost' }).click();
      await tab(page).getByText('— Walk 62 (synthetic)').waitFor();
      if (await tab(page).getByText(/^Waiting on/).count()) throw new Error('the Waiting banner still shows on a lost deal');
    });

    await step('on the lost deal Convert to client is refused with its sentence (CL4; §13.2 row 62)', async () => {
      await tab(page).getByText(LOST_SENTENCE).waitFor();
      const convert = tab(page).getByRole('button', { name: /Convert to client/ });
      if (!(await convert.isDisabled())) throw new Error('Convert to client is offered on a lost deal');
    });

    await step('Reopen deal brings Convert to client back', async () => {
      await tab(page).getByRole('button', { name: 'Reopen deal' }).click();
      await tab(page).getByRole('button', { name: 'Convert to client', exact: true }).waitFor();
      if (await tab(page).getByRole('button', { name: 'Convert to client', exact: true }).isDisabled()) {
        throw new Error('Convert to client is still refused after Reopen');
      }
    });

    await step('Convert to client makes GD2 a New client; its box becomes a link that opens the client page (CL26; slice 67)', async () => {
      await tab(page).getByRole('button', { name: 'Convert to client', exact: true }).click();
      await tab(page).getByRole('link', { name: `${spec.client} ↗` }).click();
      await page.waitForURL(/\/clients\/\d+\/overview/);
      await page.getByRole('region', { name: 'Overview' }).getByText('New client', { exact: true }).first().waitFor();
      const header = await api(page, base, `deals/${dealId}/`);
      if (header.client.relationship !== 'new_client') throw new Error(header.client.relationship);
      await page.goto(`${base}/deals/${dealId}/overview`);
    });

    await step('a FEIN typed in the header lands in intake (M24, M25)', async () => {
      await tab(page).getByRole('button', { name: /^FEIN: / }).click();
      await tab(page).getByRole('textbox', { name: 'FEIN' }).fill('12-3456789');
      await tab(page).getByRole('textbox', { name: 'FEIN' }).press('Enter');
      await tab(page).getByText('12-3456789', { exact: true }).waitFor();
      const intake = await api(page, base, `deals/${dealId}/intake/`);
      if (intake.answers.fein !== '12-3456789') throw new Error(`intake holds ${intake.answers.fein}`);
    });

    await step(`${SOLD_CLIENT}: a New client’s box is its link, and Expected revenue is its key’s $20,491 (M21, M38)`, async () => {
      const found = await api(page, base, `clients/?q=${encodeURIComponent(SOLD_CLIENT)}`);
      const row = (found.results || found).find((client) => client.name === SOLD_CLIENT);
      if (!row) throw new Error(`${SOLD_CLIENT} is not seeded: run seed_golden GD1-sold`);
      await page.goto(`${base}/deals/${row.deal.id}`);
      await page.waitForURL(/\/overview/);
      await tab(page).getByRole('link', { name: `${SOLD_CLIENT} ↗` }).waitFor();
      if (await tab(page).getByText('Not on the client book yet').count()) throw new Error('a client reads as a prospect');
      await tab(page).locator('.bb-stat-card', { hasText: 'Expected revenue' }).getByText('$20,491').waitFor();
    });
  },
};
