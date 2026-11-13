// Slice 68's "done when" (plan.md §13.10 row 68; §8.5; CL13, CL24, CL25, H106): a task added on GD1-sold's client Agenda
// shows on the deal's Agenda and in the Work queue, and Later holds it; a 60/40 client split saves; an own-tier producer
// sees only their own share. Run with `--need s68` on a fresh GD1-sold (`seed_golden GD1-sold`): it adds a task, saves
// a client split (Dev 60 / "Walk Producer (synthetic)" 40) and rebooks the deal through the API so its records take it,
// so seed GD1-sold again afterwards. The own-tier producer is the dev DB's synthetic `walk-producer` (no Profile: the
// own tier; LOOK_PRODUCER_USER / LOOK_PRODUCER_PASSWORD override it).

import { spec as goldenSpec } from '../shared/golden.mjs';

const SOLD = goldenSpec('GD1-sold');
const TASK = 'Walk 68: call HR about the renewal (synthetic)';
const SECOND = 'Walk Producer (synthetic)';
const PRODUCER = {
  name: process.env.LOOK_PRODUCER_USER || 'walk-producer',
  password: process.env.LOOK_PRODUCER_PASSWORD || 'walk-producer-pw',
};

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

function dayAfter(iso, days) {
  const day = new Date(`${iso}T00:00:00Z`);
  return new Date(day.getTime() + days * 86400000).toISOString().slice(0, 10);
}

const region = (page, name) => page.getByRole('region', { name, exact: true });
const nav = (page) => page.getByRole('navigation', { name: 'Client sections' });
const taskOf = (rows) => rows.find((row) => row.label === TASK || row.title === TASK);

export const clientpage68 = {
  title: "Slice 68: GD1-sold's client Agenda and Commissions — a task lands on the deal and the Work queue and Later holds it; a 60/40 client split saves; an own-tier producer sees only their own share",
  deal: 'GD1-sold',
  async run(ctx, { signIn }) {
    const { page, step, base } = ctx;
    await signIn(ctx);
    let client;
    let dealId;
    let today;

    await step(`${SOLD.client}'s page: the rollup chip, then Upkeep · Agenda and Revenue · Commissions in the nav (CL13)`, async () => {
      const found = await api(page, base, 'GET', `clients/?q=${encodeURIComponent(SOLD.client)}`);
      client = (found.results || found).find((row) => row.name === SOLD.client);
      if (!client) throw new Error(`"${SOLD.client}" is not seeded: run seed_golden GD1-sold`);
      const agenda = await api(page, base, 'GET', `clients/${client.id}/agenda/`);
      today = agenda.today;
      dealId = agenda.deals[0]?.deal.id;
      const rows = agenda.deals.flatMap((panel) => panel.rows);
      if (taskOf(rows)) throw new Error('the walk task is already there: run seed_golden GD1-sold first');
      await page.goto(`${base}/clients/${client.id}/overview`);
      const side = page.locator('.bb-sidebar');
      await side.locator('.bnf-cw-sidechips').getByText(/^(on track|\d+ due soon|\d+ overdue)$/).waitFor();
      await side.getByText('Upkeep', { exact: true }).waitFor();
      await side.getByText('Revenue', { exact: true }).waitFor();
      await nav(page).getByRole('link', { name: /^Agenda/ }).click();
      await page.waitForURL(/\/clients\/\d+\/agenda$/);
    });

    await step("the Agenda: Add a task (no deal pick with one deal), the deal's panel with All of this deal's tasks ▸, Done (CL24)", async () => {
      const tab = region(page, 'Agenda');
      await tab.getByText('Add a task', { exact: true }).waitFor();
      if (await tab.getByLabel('On', { exact: true }).count()) throw new Error('a deal pick shows with one deal');
      const panel = tab.getByRole('region', { name: /^Deal renewing \d{2}\/\d{2}\/\d{4} · Sold$/ });
      await panel.getByText(/Next: Sold\./).waitFor();
      await panel.getByRole('link', { name: "All of this deal's tasks ▸" }).waitFor();
      await tab.getByText('Done', { exact: true }).waitFor();
    });

    await step('adding a task due in two days lands it in the panel\'s Up next, and the rollup reads "1 due soon"', async () => {
      const tab = region(page, 'Agenda');
      await tab.getByLabel('Task', { exact: true }).fill(TASK);
      await tab.getByLabel('Due', { exact: true }).fill(dayAfter(today, 2));
      await tab.getByRole('button', { name: 'Add', exact: true }).click();
      await page.getByText('Task added').first().waitFor();
      await tab.locator('.bnf-ag-item', { hasText: TASK }).waitFor();
      await page.locator('.bnf-cw-sidechips').getByText('1 due soon', { exact: true }).waitFor();
    });

    await step("All of this deal's tasks ▸ opens the deal's own Agenda, which holds the task", async () => {
      await region(page, 'Agenda').getByRole('link', { name: "All of this deal's tasks ▸" }).click();
      await page.waitForURL(new RegExp(`/deals/${dealId}/agenda$`));
      await page.locator('.bnf-ag-item', { hasText: TASK }).waitFor();
    });

    await step('the Work queue lists the task, due in two days', async () => {
      const queue = await api(page, base, 'GET', 'work-queue/');
      const row = queue.rows.find((entry) => entry.kind === 'task' && entry.label === TASK);
      if (!row || row.due !== dayAfter(today, 2)) throw new Error(`queue row: ${JSON.stringify(row)}`);
      await page.goto(`${base}/`);
      await page.getByRole('tab', { name: 'Work queue' }).click();
      await page.getByText(TASK).first().waitFor();
    });

    await step('Later ▸ In 3 days on the client Agenda moves the task; the deal and the Work queue hold the new day', async () => {
      await page.goto(`${base}/clients/${client.id}/agenda`);
      const row = region(page, 'Agenda').locator('.bnf-ag-item', { hasText: TASK });
      await row.getByRole('button', { name: 'Later', exact: true }).click();
      await row.getByRole('button', { name: 'In 3 days' }).click();
      await row.locator('form').getByRole('button', { name: 'Later' }).click();
      await page.getByText('Task moved').first().waitFor();
      const moved = dayAfter(today, 3);
      const own = await api(page, base, 'GET', `deals/${dealId}/agenda/`);
      if (taskOf(own.rows)?.date !== moved) throw new Error(`deal agenda: ${JSON.stringify(taskOf(own.rows))}`);
      const queue = await api(page, base, 'GET', 'work-queue/');
      if (queue.rows.find((entry) => entry.label === TASK)?.due !== moved) throw new Error('the Work queue kept the old day');
      await page.reload();
      const label = new Date(`${moved}T00:00:00Z`).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
      });
      await region(page, 'Agenda').locator('.bnf-ag-item', { hasText: TASK }).getByText(label).waitFor();
    });

    await step('Commissions: the tiles and Booked, by plan year — 2027, Cigna and UnitedHealthcare at 5 % (CL25)', async () => {
      await nav(page).getByRole('link', { name: /^Commissions/ }).click();
      await page.waitForURL(/\/clients\/\d+\/commissions$/);
      const tab = region(page, 'Commissions');
      await tab.locator('.bb-stat-card', { hasText: 'Expected / yr' }).getByText('$20,491').waitFor();
      await tab.locator('.bb-stat-card', { hasText: 'House share' }).waitFor();
      await tab.getByText('Plan year 2027').waitFor();
      await tab.getByRole('cell', { name: 'Cigna', exact: true }).waitFor();
      await tab.getByRole('cell', { name: 'UnitedHealthcare', exact: true }).waitFor();
      await tab.locator('.bb-panel-title', { hasText: 'Who gets what on this client' }).waitFor();
    });

    await step(`a 60/40 client split (Dev, and ${SECOND} at 40 %) previews 24.0 % / 16.0 % and saves for the client (H106)`, async () => {
      const tab = region(page, 'Commissions');
      await tab.getByLabel('Primary producer').selectOption({ label: 'Dev' });
      await tab.getByRole('button', { name: '＋ Secondary producer' }).click();
      await tab.getByLabel('Person', { exact: true }).selectOption({ label: SECOND });
      const amount = tab.getByLabel('Split amount');
      await amount.fill('40');
      await amount.press('Enter');
      await tab.getByText('24.0%').first().waitFor();
      await tab.getByText('16.0%').first().waitFor();
      await tab.getByRole('button', { name: 'Save for this client' }).click();
      await tab.getByText('set on the client — applies to every deal').waitFor();
      await page.reload();
      await region(page, 'Commissions').getByText('set on the client — applies to every deal').waitFor();
      const saved = await api(page, base, 'GET', `clients/${client.id}/commission/split/`);
      const rows = saved.split.rows.map((row) => `${row.role}:${row.name}:${row.amount_label}`);
      if (rows.join('|') !== `primary:Dev:|secondary:${SECOND}:40%`) throw new Error(rows.join(', '));
    });

    await step('Rebook (API, the all tier) carries the client split into the records: House, Primary Dev, Secondary', async () => {
      await api(page, base, 'POST', `deals/${dealId}/commission/book/`);
      await page.reload();
      const chips = region(page, 'Commissions').locator('.bnf-cw-stmt-table .bnf-com-chip');
      await chips.filter({ hasText: SECOND }).first().waitFor();
      await chips.filter({ hasText: 'House' }).first().waitFor();
    });

    await step(`signed in as ${PRODUCER.name} (the own tier), the tab shows "Your share" and only their own share`, async () => {
      const context = await page.context().browser().newContext({ viewport: { width: 1440, height: 900 } });
      const own = await context.newPage();
      try {
        await own.goto(`${base}/login`);
        await own.getByLabel('Username').fill(PRODUCER.name);
        await own.getByLabel('Password').fill(PRODUCER.password);
        await own.getByRole('button', { name: /sign in|log in/i }).click();
        await own.getByLabel(/search clients/i).waitFor();
        await own.goto(`${base}/clients/${client.id}/commissions`);
        const tab = region(own, 'Commissions');
        await tab.getByText('Your share', { exact: true }).waitFor();
        if (await tab.locator('.bb-stat-card', { hasText: 'House share' }).count()) throw new Error('the own tier sees the house');
        const chips = tab.locator('.bnf-cw-stmt-table .bnf-com-chip');
        await chips.first().waitFor();
        const words = await chips.allInnerTexts();
        if (words.length !== 2 || words.some((text) => !text.includes(SECOND) || !text.includes('16.0%'))) {
          throw new Error(`chips: ${words.join(' | ')}`);
        }
        const book = await api(own, base, 'GET', `clients/${client.id}/commission/records/`);
        const roles = book.rows.flatMap((row) => row.shares.map((share) => share.role));
        if (book.tier !== 'own' || roles.join(',') !== 'secondary,secondary' || 'house' in book.totals) {
          throw new Error(`own tier read: ${book.tier} ${roles.join(',')}`);
        }
      } finally {
        await context.close();
      }
    });
  },
};
