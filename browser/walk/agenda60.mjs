// Slice 60's "done when" (plan.md §13.10 row 60; I44, I49–I53, I15–I16, I22; OQ90, OQ92): GD3's next step reads "Add
// the census, or type enrollment in the Advisor"; Later holds a step until its day. Run it with `--need s60` on a
// freshly seeded GD3 (`manage.py seed_golden GD3`), which it leaves with two current plans: seed GD3 again afterwards.
//
// GD3 as seeded prices every quote from its typed whole-line counts (checkpoint A), so the census is listed and does
// not lead (OQ90): the unread renewal packet does. The packet's two current plans then arrive through the plans API,
// as the packet's read lands them (slice 18; the quote-first walk's own step): the second stops the line figure
// (F88), plans are left with no enrollment, and the census step leads in its quote-first words, opening the Advisor's
// tier counts with "Census ▸" beside it. Later on it moves it to Later with its day and moves the next step on;
// Bring back puts it back (the day itself passing is pinned by the backend tests, at 21:00 Eastern too).

const ADD_OR_TYPE = 'Add the census, or type enrollment in the Advisor';

async function api(page, base, method, url, body) {
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

const row = (page, words) => page.locator('.bnf-ag-item', { hasText: words }).first();
const section = (page, title) => page.locator('.bnf-ag-block', { has: page.getByRole('button', { name: new RegExp(`^[▾▸] ${title}`) }) });

export const agenda60 = {
  title: 'Slice 60: GD3’s next step reads “Add the census, or type enrollment in the Advisor”; Later holds a step until its day',
  deal: 'GD3',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec, base } = ctx;
    let dealId;
    const nextStep = async () => (await api(page, base, 'GET', `deals/${dealId}/agenda/`)).next_step.label;
    await signIn(ctx);
    await openDeal(ctx);
    await step('the deal sidebar has Agenda first, before 1 · Get to Market (A21, I1)', async () => {
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      const board = await api(page, base, 'GET', `deals/${dealId}/plans/?line=medical`);
      if (board.plans.some((p) => p.role === 'current')) throw new Error('GD3 has moved on: run manage.py seed_golden GD3 first');
      await page.getByRole('link', { name: 'Agenda', exact: true }).click();
      await page.waitForURL(/\/deals\/\d+\/agenda/);
      await page.getByText('Every task on this deal', { exact: false }).waitFor();
    });
    await step('checkpoint A: typed counts price the quotes, so "Import the census" is listed but the unread packet leads (OQ90)', async () => {
      await row(page, 'Import the census').waitFor();
      await row(page, 'Read carrier quotes').waitFor();
      const label = await nextStep();
      if (label !== 'Read carrier quotes') throw new Error(`next step reads "${label}"`);
    });
    const arrive = (ref) => {
      const plan = spec.arrivals.find((p) => p.ref === ref);
      const body = { line: 'medical', role: 'current', carrier: plan.carrier, name: plan.name, values: plan.values };
      return api(page, base, 'POST', `deals/${dealId}/plans/`, body);
    };
    await step('the renewal packet’s two current plans arrive: the line figure stops pricing them (F88)', async () => {
      await arrive('D');
      await arrive('F');
      await page.reload();
      await page.getByText('Every task on this deal', { exact: false }).waitFor();
    });
    await step(`GD3’s next step reads “${ADD_OR_TYPE}”, with Open ▸ to the Advisor and Census ▸ beside it`, async () => {
      const label = await nextStep();
      if (label !== ADD_OR_TYPE) throw new Error(`next step reads "${label}"`);
      const census = row(page, ADD_OR_TYPE);
      await census.waitFor();
      const open = await census.getByRole('link', { name: 'Open ▸' }).getAttribute('href');
      if (!/\/advisor\?line=medical$/.test(open)) throw new Error(`Open ▸ goes to ${open}`);
      await census.getByRole('link', { name: 'Census ▸' }).waitFor();
    });
    await step('Later ▸ In 3 days holds the step in Later with its day and who held it; the next step moves on (I15, I16)', async () => {
      const census = row(page, ADD_OR_TYPE);
      await census.getByRole('button', { name: 'Later' }).click();
      await census.getByRole('button', { name: 'In 3 days' }).click();
      await census.getByLabel('Why it waits').fill('Client sends the census next week (synthetic)');
      await census.locator('form').getByRole('button', { name: 'Later' }).click();
      await page.getByText('Held back until then').waitFor();
      const later = section(page, 'Later');
      await later.locator('.bnf-ag-item', { hasText: ADD_OR_TYPE }).waitFor();
      await later.getByText(/^Back [A-Z][a-z]{2} \d{1,2}, \d{4} · .+ — Client sends the census next week/).waitFor();
      const label = await nextStep();
      if (label === ADD_OR_TYPE) throw new Error('the held step still leads');
    });
    await step('Bring back puts it back in Up next, and it leads again (I22)', async () => {
      const later = section(page, 'Later');
      await later.locator('.bnf-ag-item', { hasText: ADD_OR_TYPE }).getByRole('button', { name: 'Bring back' }).click();
      await page.getByText('Back on the Agenda').waitFor();
      await section(page, 'Up next').locator('.bnf-ag-item', { hasText: ADD_OR_TYPE }).waitFor();
      const label = await nextStep();
      if (label !== ADD_OR_TYPE) throw new Error(`next step reads "${label}"`);
    });
    await step('a task added by hand lands in Up next, and ✓ moves it to Done (I27, I31)', async () => {
      await page.getByLabel('Task').fill('Ask HR for the census (synthetic)');
      await page.getByRole('button', { name: 'Add', exact: true }).click();
      await page.getByText('Task added').waitFor();
      const task = section(page, 'Up next').locator('.bnf-ag-item', { hasText: 'Ask HR for the census' });
      await task.getByRole('button', { name: 'Mark this task done' }).click();
      await page.getByText('Task done').waitFor();
      await page.getByRole('button', { name: /^▸ Done/ }).click();
      await section(page, 'Done').locator('.bnf-ag-item', { hasText: 'Ask HR for the census' }).waitFor();
    });
  },
};
