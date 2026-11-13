// Slice 67's "done when" (plan.md §13.10 row 67; §8.5; CL13–CL23, CL26, G116; OQ101): GD1-sold opens on its client page
// from Clients, in the old ClientWorkspace's blocks; the ways in (the Plan year block, the deal sidebar's client block,
// the header's client name) go between the deal and its client; GD2's page offers Convert to client, which makes it a
// New client with an Activity row; the Notes tab saves the standing brief; on GD6, History's chips open the deal's
// Intake, Census and Questionnaire. Run with `--need s67` on fresh GD2 and GD6 (`seed_golden GD2 GD6`): it converts
// GD2, types its brief and lands a 60-person census on GD6 (API, as slice 40's walk does), so seed both again
// afterwards. GD1-sold is only read.

import { spec as goldenSpec } from '../shared/golden.mjs';

const SOLD = goldenSpec('GD1-sold');
const GD6 = goldenSpec('GD6');
const BRIEF = 'Walk 67: the owner decides, HR executes (synthetic).';

async function api(page, base, method, url, options = {}) {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
  const response = await page.request.fetch(`${base}/api/${url}`, {
    method,
    ...options,
    headers: { 'X-CSRFToken': csrf, Referer: base },
  });
  if (!response.ok()) throw new Error(`${method} ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

async function dealOf(page, base, client) {
  const found = await api(page, base, 'GET', `clients/?q=${encodeURIComponent(client)}`);
  const row = (found.results || found).find((entry) => entry.name === client);
  if (!row) throw new Error(`"${client}" is not seeded: run seed_golden`);
  return row;
}

/** GD6's 60 enrolled employees as a census file: the current plan's 30 EE, 10 ES, 8 EC and 12 FAM (synthetic). */
function censusCsv(plan) {
  const head = ['Employee ID', 'Relationship', 'First Name', 'Last Name', 'Date of Birth', 'Gender', 'Zip Code',
    'Hours Per Week', 'Medical Plan', 'Medical Tier'];
  const tiers = [...Array(30).fill('EE'), ...Array(10).fill('ES'), ...Array(8).fill('EC'), ...Array(12).fill('FAM')];
  const rows = tiers.map((tier, i) => {
    const n = i + 1;
    return [`W7-${String(n).padStart(3, '0')}`, 'Employee', `Walker${n}`, `Synthetic${n}`,
      `19${70 + (n % 25)}-0${1 + (n % 9)}-1${n % 9}`, n % 2 ? 'F' : 'M', '33602', '40', plan, tier];
  });
  return [head, ...rows].map((row) => row.join(',')).join('\n');
}

const tab = (page) => page.getByRole('region', { name: 'Overview' });
const top = async (locator) => (await locator.first().boundingBox()).y;
const clientUrl = /\/clients\/\d+\/overview/;

export const clientpage67 = {
  title: "Slice 67: the client page — GD1-sold in the old ClientWorkspace's blocks, the ways in, GD2's Convert to client, GD6's History chips",
  deal: 'GD2',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec, base } = ctx;
    await signIn(ctx);

    await step(`Clients lists ${SOLD.client}; its row opens the client page (CL26)`, async () => {
      await page.goto(`${base}/?view=book`);
      await page.getByLabel(/search clients/i).fill(SOLD.client);
      await page.getByRole('link', { name: SOLD.client }).first().click();
      await page.waitForURL(clientUrl);
    });

    await step('its sidebar: ← Clients, the name, Owner, Effective, New client; Overview and Notes; the 2027 Plan year block', async () => {
      const side = page.locator('.bb-sidebar');
      await side.getByRole('link', { name: '← Clients' }).waitFor();
      await side.getByText('New client', { exact: true }).waitFor();
      await side.getByText(/^Effective /).waitFor();
      await side.getByRole('navigation', { name: 'Client sections' }).getByRole('link', { name: 'Notes' }).waitFor();
      await side.getByText('Plan year', { exact: true }).waitFor();
      await side.getByText(/^\d{4} sections$/).waitFor();
      await side.getByRole('navigation', { name: /deal's sections/ }).getByRole('link', { name: 'Overview' }).waitFor();
      await side.getByText('This year at a glance').waitFor();
    });

    await step('the Overview stands in the old order: title row, header card, Waiting banner, tiles, Deal card, Coverage in force, Activity', async () => {
      const region = tab(page);
      const order = [
        ['title row', region.getByText(/^Who this client is, where the year stands/)],
        ['header', region.locator('.bnf-ov-name', { hasText: SOLD.client })],
        ['banner', region.locator('.bnf-cw-banner')],
        ['tiles', region.locator('.bb-metric-row').getByText('Expected revenue', { exact: true })],
        ['Deal card', region.getByText(/^The \d{4} deal — effective /)],
        ['Coverage in force', region.getByText('Coverage in force', { exact: true })],
        ['Activity', region.locator('.bnf-ov-activity')],
      ];
      let last = -1;
      for (const [name, locator] of order) {
        const y = await top(locator);
        if (y < last) throw new Error(`${name} stands above the block before it`);
        last = y;
      }
    });

    await step("the sold deal's facts: $20,491 expected, the sold plans' carriers at 5%, the conversion in Activity, History", async () => {
      const region = tab(page);
      await region.locator('.bb-stat-card', { hasText: 'Expected revenue' }).getByText('$20,491').waitFor();
      const coverage = region.locator('.bnf-cw-table');
      await coverage.getByText('Cigna, UnitedHealthcare').waitFor();
      await coverage.getByText(/^5%/).waitFor();
      await region.getByText('Now a new client (a plan was sold)').first().waitFor();
      await region.locator('.bnf-cw-history-row').getByText(/Cigna, UnitedHealthcare/).waitFor();
      if (await region.getByRole('button', { name: 'Convert to client' }).count()) throw new Error('a client is offered Convert');
    });

    await step("the Plan year's Overview opens the deal; its sidebar block and its header name lead back (CL14, CL26)", async () => {
      const year = () => page.getByRole('navigation', { name: /deal's sections/ });
      await year().getByRole('link', { name: 'Overview' }).click();
      await page.waitForURL(/\/deals\/\d+\/overview/);
      await page.locator('.bb-sidebar').getByRole('link', { name: `${SOLD.client} ↗` }).click();
      await page.waitForURL(clientUrl);
      await year().getByRole('link', { name: 'Agenda' }).click();
      await page.waitForURL(/\/deals\/\d+\/agenda/);
      await page.locator('.bnf-ov-header').getByRole('link', { name: SOLD.client, exact: true }).click();
      await page.waitForURL(clientUrl);
    });

    let clientId;
    await step(`GD2's header name opens its client page: ← Prospects, Prospect, Convert to client`, async () => {
      await page.goto(`${base}/`);
      await openDeal(ctx);
      await page.locator('.bnf-ov-header').first().getByRole('link', { name: spec.client, exact: true }).click();
      await page.waitForURL(clientUrl);
      clientId = Number(page.url().match(/\/clients\/(\d+)/)[1]);
      const detail = await api(page, base, 'GET', `clients/${clientId}/`);
      if (detail.relationship !== 'prospect') throw new Error('GD2 is not a prospect: run seed_golden GD2 first');
      await page.locator('.bb-sidebar').getByRole('link', { name: '← Prospects' }).waitFor();
      await tab(page).getByRole('button', { name: 'Convert to client', exact: true }).waitFor();
    });

    await step('Convert to client makes GD2 a New client, with its Activity row on the page (CL15, OQ101)', async () => {
      await tab(page).getByRole('button', { name: 'Convert to client', exact: true }).click();
      await page.locator('.bb-sidebar').getByText('New client', { exact: true }).waitFor();
      await tab(page).getByText('Converted to a client').first().waitFor();
      if (await tab(page).getByRole('button', { name: 'Convert to client' }).count()) throw new Error('Convert still offered');
      const detail = await api(page, base, 'GET', `clients/${clientId}/`);
      if (detail.relationship !== 'new_client' || !detail.client_since) throw new Error(JSON.stringify(detail));
      const feed = await api(page, base, 'GET', `clients/${clientId}/activity/`);
      if (!feed.results.some((row) => row.area === 'client' && row.action === 'converted')) throw new Error('no Activity row');
    });

    await step('Notes: the standing brief saves on blur and heads the Overview (CL23)', async () => {
      const sections = page.getByRole('navigation', { name: 'Client sections' });
      await sections.getByRole('link', { name: 'Notes', exact: true }).click();
      await page.waitForURL(/\/clients\/\d+\/notes/);
      await page.getByRole('textbox', { name: 'Standing brief' }).fill(BRIEF);
      await page.getByRole('textbox', { name: 'A new note' }).click();
      await page.getByText('Standing brief saved').waitFor();
      const detail = await api(page, base, 'GET', `clients/${clientId}/`);
      if (detail.notes !== BRIEF) throw new Error(`notes: ${detail.notes}`);
      await sections.getByRole('link', { name: 'Overview', exact: true }).click();
      await tab(page).locator('.bnf-ov-legal', { hasText: BRIEF }).waitFor();
    });

    let gd6;
    await step("GD6 gets its 60-person census (API: upload, import, Apply), then opens on its client page", async () => {
      gd6 = await dealOf(page, base, GD6.client);
      const plan = GD6.plans.find((p) => p.role === 'current').name;
      const document = await api(page, base, 'POST', `deals/${gd6.deal.id}/documents/`, {
        multipart: {
          file: { name: 'Walk 67 census (synthetic).csv', mimeType: 'text/csv', buffer: Buffer.from(censusCsv(plan)) },
          kind: 'census',
          lines: '[]',
        },
      });
      const proposed = await api(page, base, 'POST', `deals/${gd6.deal.id}/census/imports/`, {
        data: { document_id: document.id },
      });
      await api(page, base, 'POST', `census/imports/${proposed.id}/apply/`);
      await page.goto(`${base}/clients/${gd6.id}/overview`);
      await tab(page).locator('.bnf-cw-history-row').waitFor();
    });

    for (const [chip, where] of [
      ['Intake', /\/deals\/\d+\/intake/],
      ['Census 60 EE', /\/deals\/\d+\/census/],
      ['Questionnaire', /\/deals\/\d+\/questionnaire\?form=/],
    ]) {
      await step(`on GD6, History's "${chip}" chip opens the deal's ${chip.split(' ')[0]} (G116)`, async () => {
        await page.goto(`${base}/clients/${gd6.id}/overview`);
        await tab(page).locator('.bnf-cw-history-row').getByRole('button', { name: chip }).click();
        await page.waitForURL(where);
        if (!page.url().includes(`/deals/${gd6.deal.id}/`)) throw new Error(`opened ${page.url()}`);
      });
    }
  },
};
