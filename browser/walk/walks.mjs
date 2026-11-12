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
        for (const plan of currents) await page.getByText(plan.name, { exact: false }).first().waitFor();
      });
    },
  },
};
