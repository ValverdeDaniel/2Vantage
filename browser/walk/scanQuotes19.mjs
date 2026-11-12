// Need 1, scan quotes (plan.md §13.7 row 19, "done when"; V.2 need 1; D28, D72–D75, E75, E78; Q.9 row 19): on GD3 the
// renewal packet is read again from Documents' ↻ Re-read… panel, its review shows the two current plans and their
// renewals in the file's order with the printed counts unticked, "Use this scan ▸" makes them plans (the renewals
// linked) and moves the deal to Quoting, and ↶ Undo this run takes them off again. A direct person's read landing at
// once is slice 20's half of need 1.
//
// Run it with `--need 1` on a freshly seeded GD3 (`manage.py seed_golden GD3`), which it leaves at checkpoint A again
// (Quoting: the stage only moves forward). It makes ONE REAL Claude read (Sonnet 5.5, about $0.05 of the build's $20
// cap, `manage.py ai_spend`); the backend needs ANTHROPIC_API_KEY and the worker must be running.

const READ_MS = 300000; // a real read of the packet takes about a minute

export const scanQuotes19 = {
  title: 'Scan quotes: the renewal packet is reviewed, used as plans in printed order, and undone (D28, D72–D75)',
  deal: 'GD3',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const packet = spec.renewal_packet;
    const [first, second] = spec.arrivals.map((plan) => plan.name);
    await signIn(ctx);
    await openDeal(ctx);

    await step('Documents opens on the packet, with ↻ Re-read… under it', async () => {
      await page.getByRole('link', { name: 'Documents', exact: true }).click();
      await page.getByRole('tab', { name: /2027 Renewal/ }).first().click();
      await page.getByRole('button', { name: '↻ Re-read…' }).waitFor();
    });
    await step('the Re-read panel ticks the packet; "Re-read 1 file" starts Claude’s read', async () => {
      await page.getByRole('button', { name: '↻ Re-read…' }).click();
      await page.getByText('nothing on the deal changes until you use it').waitFor();
      await page.getByRole('button', { name: 'Re-read 1 file' }).click();
      await page.getByText(/Claude is reading the file/).waitFor({ timeout: 30000 });
    });
    await step('the read waits for review: the staged banner and "Review this scan"', async () => {
      await page.getByText('Review this scan').waitFor({ timeout: READ_MS });
      await page.getByText(/Claude re-read the quotes — nothing has changed yet/).waitFor();
    });
    await step('the review shows the current plans and their renewals in the file’s order, counts unticked', async () => {
      const heads = await page
        .getByRole('table')
        .filter({ hasText: 'NEW · Current' })
        .locator('thead th')
        .evaluateAll((ths) => ths.slice(1).map((th) => th.innerText.replace(/\s+/g, ' ')));
      const order = heads.map((text) => (/Current/.test(text) ? 'current' : /Renewal/.test(text) ? 'renewal' : '?'));
      if (order.join() !== 'current,renewal,current,renewal') throw new Error(`columns: ${heads.join(' | ')}`);
      if (!heads[1].includes(`Renews ${first}`) || !heads[3].includes(`Renews ${second}`)) {
        throw new Error('a renewal does not name its current plan');
      }
      const counts = page.getByRole('checkbox', { name: new RegExp(`${packet.carrier} ${first}`) });
      if (await counts.isChecked()) throw new Error('the printed counts arrived ticked');
    });
    await step('"Use this scan ▸" makes the plans and moves the deal to Quoting', async () => {
      await page.getByRole('button', { name: 'Use this scan ▸' }).click();
      await page.getByText('✓ Used Claude’s read — 2 current plans · 2 renewals').waitFor({ timeout: 30000 });
      await page.getByText('Quoting', { exact: true }).first().waitFor();
    });
    await step('the Advisor shows both current plans and their renewals', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByText(first).filter({ visible: true }).first().waitFor();
      await page.getByText(second).filter({ visible: true }).first().waitFor();
    });
    await step('↶ Undo this run takes the plans off again', async () => {
      await page.getByRole('link', { name: 'Documents', exact: true }).click();
      await page.getByRole('button', { name: '↶ Undo this run' }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByRole('button', { name: 'Undo this run', exact: true }).click();
      await page.getByText(/Undone — the deal is back to how it was before that read/).waitFor({ timeout: 30000 });
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByText(spec.plans[0].name).filter({ visible: true }).first().waitFor();
      // the board refetches after the Undo: wait for the read's plans to leave it
      await page.getByText(second).filter({ visible: true }).first().waitFor({ state: 'hidden', timeout: 30000 });
    });
  },
};
