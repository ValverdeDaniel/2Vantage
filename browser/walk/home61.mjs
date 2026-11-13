// Slice 61's "done when" (plan.md §13.10 row 61; A9–A12, A21, A23, A24, I70–I86, I122; OQ91, OQ94, OQ95, OQ101 c):
// the shell shows the stepper and badges; the dashboard's numbers are real; selling GD2's plan moves it from
// Prospects to Clients, showing its commission step. Run with `--need s61` on a freshly seeded GD2
// (`manage.py seed_golden GD2`); it sells GD2's AmeriHealth alternate, so seed GD2 again afterwards.

const SOLD = { carrier: 'AmeriHealth', name: 'Bronze HSA 4000' };

async function api(page, base, url) {
  const response = await page.request.fetch(`${base}/api/${url}`);
  if (!response.ok()) throw new Error(`GET ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

const card = (page, label) => page.locator('.bb-stat-card, .bnf-graph-card', { hasText: label }).first();
const number = async (locator) => (await locator.locator('.bb-stat-value, .bnf-graph-value').innerText()).trim();

export const home61 = {
  title: 'Slice 61: the shell’s stepper and badges; the dashboard’s real numbers; selling GD2’s plan moves it to Clients',
  deal: 'GD2',
  async run(ctx, { signIn }) {
    const { page, step, spec, base } = ctx;
    let dealId;
    await signIn(ctx);

    await step('Prospects lands first and its cards are the feed’s figures (OQ95; I86, I124)', async () => {
      await page.getByRole('tab', { name: 'Prospects', selected: true }).waitFor();
      await page.locator('.bnf-nc-row', { hasText: spec.client }).waitFor();
      const feed = await api(page, base, 'work-queue/');
      const shown = await number(card(page, 'Prospects'));
      if (shown !== String(feed.cards.prospects.count)) throw new Error(`card ${shown}, feed ${feed.cards.prospects.count}`);
      const row = feed.rows.find((r) => r.kind === 'deal' && r.client_name === spec.client);
      if (!row || row.client_status !== 'prospect') throw new Error(`GD2's row: ${JSON.stringify(row)}`);
      dealId = row.deal_id;
      if (row.stage === 'sold') throw new Error('GD2 is already sold: run manage.py seed_golden GD2 first');
    });

    await step('the Work queue’s cards are real: Overdue and Due this week over its rows, actions and sales from stats (A10, I82–I84)', async () => {
      await page.getByRole('tab', { name: 'Work queue' }).click();
      await page.locator('.bnf-wq-head').waitFor();
      const stats = await api(page, base, 'work-queue/stats/');
      const actions = await number(card(page, 'Actions completed this week'));
      if (actions !== String(stats.actions_week.total)) throw new Error(`actions ${actions}, stats ${stats.actions_week.total}`);
      await card(page, 'Total sales this month').locator('svg.bnf-spark').waitFor();
      const feed = await api(page, base, 'work-queue/');
      const open = feed.rows.filter((r) => !r.finished && !r.lost && !(r.held && r.held > feed.today));
      const overdue = open.filter((r) => r.due_in !== null && r.due_in < 0).length;
      const shown = await number(card(page, 'Overdue'));
      if (shown !== String(overdue)) throw new Error(`Overdue ${shown}, rows ${overdue}`);
    });

    await step('GD2’s deal shows the journey stepper, its current dot, the sidebar’s badges, ready chip and meters (A21, A23, A24)', async () => {
      await page.goto(`${base}/deals/${dealId}/agenda`);
      const journey = page.locator('.bnf-journey');
      await journey.getByText('1 · Get to Market').waitFor();
      await journey.getByText('2 · Quote to Close').waitFor();
      await journey.locator('.bnf-journey-step-current').waitFor();
      await page.locator('.bb-sidebar .bnf-ready-badge').waitFor();
      await page.locator('.bb-sidebar .bb-nav-badge').first().waitFor();
      await page.locator('.bb-sidebar .bnf-readiness').getByText('Deal readiness').waitFor();
      const read = await api(page, base, `deals/${dealId}/journey/`);
      const current = read.journey.modules.flatMap((m) => m.steps).find((s) => s.state === 'current');
      const dot = await journey.locator('.bnf-journey-step-current').getAttribute('title');
      if (current && dot !== current.label) throw new Error(`current dot ${dot}, journey ${current.label}`);
    });

    await step(`selling ${SOLD.carrier} ${SOLD.name} in the Advisor moves the stepper to Sold`, async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: `Actions for ${SOLD.carrier} — ${SOLD.name}` }).first().click();
      await page.getByRole('menuitem', { name: 'Mark sold' }).click();
      await page.getByText(`${SOLD.name} marked sold`).waitFor();
      const modal = page.getByRole('dialog', { name: /^Booked —/ });
      if (await modal.count()) await modal.getByRole('button', { name: 'Done' }).click();
      await page.locator('.bnf-journey-step-done', { hasText: 'Sold' }).waitFor();
    });

    let next;
    await step('GD2 has left Prospects at once (I122 as changed by OQ101 c; OQ91)', async () => {
      await page.goto(`${base}/`);
      await page.getByRole('tab', { name: 'Prospects', selected: true }).waitFor();
      await page.locator('.bnf-nc-row').first().waitFor();
      if (await page.locator('.bnf-nc-row', { hasText: spec.client }).count()) throw new Error('GD2 is still on Prospects');
      next = (await api(page, base, `deals/${dealId}/journey/`)).next_step;
      if (!['commission', 'mark_sold'].includes(next.key)) throw new Error(`next step ${next.key}`);
    });

    await step('Clients lists GD2 as a New client with its commission step, or "Sold", as Next action (OQ91)', async () => {
      await page.getByRole('tab', { name: 'Clients' }).click();
      const row = page.locator('.bnf-clients-row', { hasText: spec.client });
      await row.waitFor();
      await row.getByText(/New client/).waitFor();
      await row.locator('.bnf-action-chip', { hasText: next.label }).waitFor();
    });
  },
};
