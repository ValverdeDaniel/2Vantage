// Slice 42's "done when" (plan.md §13.9 row 42; G1–G55, G133, G134): on GD6 Florida Blue 51+ is chosen by the band,
// with one plans row per current plan; the officer's signature locks the form. Run it with `--need s42` on a freshly
// seeded GD6 (`seed_golden GD6`); it leaves GD6's questionnaire signed, so seed it again afterwards.
//
// Everything is done as a person does it: the sidebar's Questionnaire link, the Intake checklist's picker, the four
// blank required answers typed and picked, the authorization ticked and the officer's name signed.

export const questionnaire42 = {
  title: "Slice 42: on GD6 Florida Blue 51+ is chosen by the band, a plans row per current plan; the officer's signature locks it",
  deal: 'GD6',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const currents = spec.plans.filter((p) => p.line === 'medical' && p.role === 'current');
    const officer = spec.get_to_market.contacts[0].name;
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Intake checklist picks the form by group size: "Auto by group size — Florida Blue 51+"', async () => {
      await page.getByRole('link', { name: 'Intake', exact: true }).click();
      const row = page.getByRole('group', { name: /questionnaire/i }).first();
      await row.getByText('Fillable form:').waitFor();
      const picked = await row.locator('select').inputValue();
      if (picked !== 'auto') throw new Error(`the picker says ${picked}`);
      await row.getByRole('option', { name: 'Auto by group size — Florida Blue 51+' }).waitFor({ state: 'attached' });
    });
    await step('the sidebar shows Questionnaire under 1 · Get to Market, and it opens on Florida Blue 51+', async () => {
      await page.getByRole('link', { name: 'Questionnaire', exact: true }).click();
      await page.waitForURL(/\/questionnaire/);
      await page.getByRole('heading', { name: 'Florida Blue Underwriting Questionnaire' }).waitFor();
    });
    await step(`one plans row per current plan: ${currents.map((p) => p.name).join(', ')}`, async () => {
      const chips = page.getByText(/^Plan \d+$/);
      if ((await chips.count()) !== currents.length) throw new Error(`${await chips.count()} plan rows`);
      for (const plan of currents) {
        const boxes = page.getByLabel('Plan Name/Description');
        const values = await boxes.evaluateAll((els) => els.map((el) => el.value));
        if (!values.includes(plan.name)) throw new Error(`no plan row reads ${plan.name}: ${values.join(', ')}`);
      }
    });
    await step('the company facts are filled in from the deal', async () => {
      const name = await page.getByLabel('1. Name of Business').inputValue();
      if (name !== spec.intake.answers.legal_name) throw new Error(`Name of Business reads ${name}`);
    });
    await step('the four blank required answers are given, and the form reaches 100% complete', async () => {
      await page.getByLabel(/^10\. Has this group had Florida Blue/).selectOption('No');
      await page.getByLabel('12. Reason for Current Bid Request').selectOption('Renewal Increase');
      await page.getByLabel(/^16\. Within the past 12 months/).selectOption('No');
      const print = page.getByLabel('Print Name of Authorized Company Officer');
      await print.fill(officer);
      await print.press('Tab');
      await page.getByText('100% complete').waitFor();
    });
    await step('signing for the company officer needs the authorization tick, then asks first', async () => {
      await page.getByLabel('Signer’s full name').fill(officer);
      const sign = page.getByRole('button', { name: 'Sign for the company officer' });
      if (await sign.isEnabled()) throw new Error('signing was offered without the authorization');
      await page.getByLabel(/written authorization to sign for them/).check();
      await sign.click();
      const dialog = page.getByRole('dialog');
      await dialog.getByText(/attests to every answer on the form and locks it/).waitFor();
      await dialog.getByRole('button', { name: 'Sign', exact: true }).click();
    });
    await step(`the form reads "Signed by ${officer} — the form is now read-only." and nothing can be typed`, async () => {
      await page.getByText(`Signed by ${officer} — the form is now read-only.`).waitFor();
      await page.getByText(`${officer} · signed`).waitFor();
      if (await page.getByLabel('1. Name of Business').isEnabled()) throw new Error('the form still takes typing');
    });
    await step('the Intake checklist reads the questionnaire done, and the picker can no longer swap it', async () => {
      await page.getByRole('link', { name: 'Intake', exact: true }).click();
      const row = page.getByRole('group', { name: /questionnaire/i }).first();
      await row.getByText('Signed — the form can no longer be swapped.').waitFor();
      if (await row.locator('select').isEnabled()) throw new Error('the picker still swaps a signed form');
    });
  },
};
