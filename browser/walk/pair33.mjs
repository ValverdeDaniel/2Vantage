// Slice 33's "done when" (plan.md §13.8 row 33; D-219, J15, F137, OQ42; need 12): on GD1, Florida Blue's 05182 and
// 05183 print as one column on Pages, its total the pair's package; ⋯ More's Split restores two columns (and the
// builder's checks then point out one plan filed as two), and "⧉ One column with…" makes the one column again. Run with
// `--need s33`. It ends with the pair made again, as GD1 is seeded. The three files are held to the old app's by the
// Fidelity lane (python tools/parity/files.py --deals GD1) and by proposals/tests/test_pair_fold.py.

async function api(page, base, url) {
  const response = await page.request.fetch(`${base}/api/${url}`, { headers: { Referer: base } });
  if (!response.ok()) throw new Error(`GET ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

const named = (spec, ref) => spec.plans.find((plan) => plan.ref === ref);
const pageOf = (page, number) => page.getByRole('region', { name: new RegExp(`^Page ${number} of`) });
// A column by the name over it (its ⋯ More may list other plans' names, so the menu's words do not count).
const columnOf = (where, plan) =>
  where.locator('th').filter({ has: where.page().locator('.bnf-pg-name', { hasText: plan.name }) });
const money = (text) => Number(String(text).replace(/[^0-9.-]/g, ''));

export const pair33 = {
  title: 'Two plan numbers print as one column (J15, D-219): on GD1, Florida Blue 05182 + 05183, then Split and pair',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec, base } = ctx;
    const [first, second] = ['FB1', 'FB2'].map((ref) => named(spec, ref));
    let dealId;
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Proposal builder opens on Medical, "What the client will see"', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'Proposal builder' }).click();
      await page.getByText('What the client will see').waitFor();
      await page.getByRole('button', { name: /^Medical/ }).click();
      dealId = page.url().match(/\/deals\/(\d+)/)[1];
    });
    await step(`page 2 prints ${first.name} as one column "+ ${second.name} (one column)", and no column of its own for ${second.name}`, async () => {
      const column = columnOf(pageOf(page, 2), first);
      await column.getByText(`+ ${second.name} (one column)`).waitFor();
      await pageOf(page, 2).getByText('5 of 6 columns').waitFor();
      const alone = pageOf(page, 2).locator('th .bnf-pg-plan, th .bnf-pg-name > span').filter({ hasText: new RegExp(`^${second.name}$`) });
      if (await alone.count()) throw new Error(`${second.name} has a column of its own`);
    });
    await step("its Monthly premium is the pair's package: both halves' premiums added by quotes", async () => {
      const pages = await api(page, base, `deals/${dealId}/proposal/pages/?line=medical&preset=primary`);
      const plans = await api(page, base, `deals/${dealId}/plans/?line=medical`);
      const ids = Object.fromEntries(plans.plans.map((plan) => [plan.name, plan.id]));
      const column = pages.plans.find((plan) => plan.plan_id === ids[first.name]);
      const halves = plans.plans.filter((plan) => [first.name, second.name].includes(plan.name));
      const sum = halves.reduce((total, plan) => total + plan.premium.monthly, 0); // the walk checks; the app adds
      if (money(column.monthly) !== sum) throw new Error(`the column reads ${column.monthly}, the halves ${sum}`);
      await columnOf(pageOf(page, 2), first).waitFor();
      await page.getByText(column.monthly, { exact: true }).first().waitFor();
    });
    await step('⋯ More says "⧉ One column with …"; Split prints two columns again and the checks point it out', async () => {
      const column = columnOf(pageOf(page, 2), first);
      await column.getByText('⋯ More').click();
      await column.getByText(`⧉ One column with ${second.name}`).waitFor();
      await column.getByRole('button', { name: 'Split' }).click();
      await columnOf(pageOf(page, 2), second).waitFor();
      await pageOf(page, 2).getByText('6 of 6 columns · full').waitFor();
      const builder = await api(page, base, `deals/${dealId}/proposal/`);
      const split = builder.checks.find((item) => item.code === 'split_plan');
      if (!split || !split.text.includes('one plan filed as two')) throw new Error('no split_plan check after Split');
    });
    await step('"⧉ One column with…" on 05182 picks 05183: one column again', async () => {
      const column = columnOf(pageOf(page, 2), first);
      await column.getByText('⋯ More').click();
      await column
        .getByRole('combobox', { name: `Print ${first.name} as one column with another plan` })
        .selectOption({ label: second.name });
      await columnOf(pageOf(page, 2), first).getByText(`+ ${second.name} (one column)`).waitFor();
      await pageOf(page, 2).getByText('5 of 6 columns').waitFor();
      const builder = await api(page, base, `deals/${dealId}/proposal/`);
      if (builder.checks.some((item) => item.code === 'split_plan')) throw new Error('split_plan stays after pairing');
    });
  },
};
