// The Walk lane's scripts (plan.md §12.5, Q.2; V.2's twelve needs and each slice's "done when"). A walk does what a
// person does in Chrome and finds everything by role and visible words, never by class or id, so it survives the
// restyling slices. Each walk: { title, deal, run(ctx) }, where ctx = { page, step, base, user, spec }.
// Needs 1–12 arrive with the slices that build them (Q.9); 0 is the example the lane started with.

const signIn = async ({ page, step, base, user }) => {
  await step('the sign-in page asks for a username and password', async () => {
    await page.goto(`${base}/login`);
    await page.getByLabel('Username').fill(user.name);
    await page.getByLabel('Password').fill(user.password);
  });
  await step('signing in lands on the client list', async () => {
    await page.getByRole('button', { name: /sign in|log in/i }).click();
    await page.getByLabel(/search clients/i).waitFor();
  });
};

const openDeal = async ({ page, step, spec }) => {
  await step(`searching "${spec.client}" finds the deal`, async () => {
    await page.getByLabel(/search clients/i).fill(spec.client);
    await page.getByRole('link', { name: spec.client }).first().click();
    await page.waitForURL(/\/deals\/\d+/);
  });
};

export const WALKS = {
  0: {
    title: "Example: sign in and open GD1's Advisor",
    deal: 'GD1',
    async run(ctx) {
      const { page, step, spec } = ctx;
      await signIn(ctx);
      await openDeal(ctx);
      await step('the Advisor tab opens', async () => {
        await page.getByRole('link', { name: 'Advisor', exact: true }).click();
        await page.waitForURL(/\/deals\/\d+\/advisor/);
      });
      await step("the Advisor shows the deal's current medical plans", async () => {
        const currents = spec.plans.filter((p) => p.line === 'medical' && p.role === 'current');
        // Visible text only: the board's "Replacing:" pickers list the current plans in their (hidden) options too.
        for (const plan of currents) {
          await page.getByText(plan.name, { exact: false }).filter({ visible: true }).first().waitFor();
        }
      });
    },
  },
  10: {
    title: "Transpose the table: GD1's medical board as plans-as-columns, header frozen, kept per browser (F34, F35)",
    deal: 'GD1',
    async run(ctx) {
      const { page, step, spec } = ctx;
      await signIn(ctx);
      await openDeal(ctx);
      await step('the Advisor opens on the medical board', async () => {
        await page.getByRole('link', { name: 'Advisor', exact: true }).click();
        await page.getByRole('button', { name: /^Medical/ }).click();
        await page.getByRole('button', { name: '⇄ Transpose' }).waitFor();
      });
      const currents = spec.plans.filter((p) => p.line === 'medical' && p.role === 'current');
      await step('⇄ Transpose turns the plans into columns (every column of the line as a row)', async () => {
        await page.getByRole('button', { name: 'All columns' }).click();
        await page.getByRole('button', { name: '⇄ Transpose' }).click();
        await page.getByRole('columnheader', { name: /Benefit/ }).waitFor();
        for (const plan of currents) {
          await page.getByRole('columnheader', { name: new RegExp(plan.name, 'i') }).first().waitFor();
        }
        await page.getByRole('cell', { name: /^Monthly total/ }).waitFor();
      });
      await step('the header row stays put while the table scrolls under it', async () => {
        const head = page.getByRole('columnheader', { name: /Benefit/ });
        const row = page.getByRole('cell', { name: /^Plan Type/ });
        await row.hover();
        const before = [await head.boundingBox(), await row.boundingBox()];
        await page.mouse.wheel(0, 300);
        await page.waitForTimeout(400);
        const after = [await head.boundingBox(), await row.boundingBox()];
        if (Math.abs(after[0].y - before[0].y) > 1) throw new Error(`the header moved ${before[0].y} → ${after[0].y}`);
        if (after[1].y >= before[1].y) throw new Error('the table did not scroll');
      });
      await step('the choice is kept in this browser', async () => {
        await page.reload();
        await page.getByRole('columnheader', { name: /Benefit/ }).waitFor();
      });
      await step('⇄ Transpose again puts the plans back in rows', async () => {
        await page.getByRole('button', { name: '⇄ Transpose' }).click();
        await page.getByRole('columnheader', { name: /Monthly total/i }).waitFor();
        await page.getByRole('row', { name: new RegExp(currents[0].name) }).first().waitFor();
      });
    },
  },
};
