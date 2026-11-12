// Slice 25's "done when" (plan.md §13.8 row 25; J17, J18, J28, J47–J55, J159; needs 6–9): on GD1's Proposal builder,
// two picks for one current plan each show their own change; their option numbers are the ones the pages show; a line
// kept as-is needs no pick; a card takes its completed mark and Undo takes it off. Run with `--need s25`. It undoes
// each write it makes (POST activity/{id}/revert/), so GD1 is left as it found it.

async function api(page, base, url, method = 'GET', body = undefined) {
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

const named = (spec, ref) => spec.plans.find((plan) => plan.ref === ref);
const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
// One recommended plan's line under the Plans card: "Option 1 · Cigna LocalPlus HDHP 3000 · −$508/mo · −2.8% · …".
const pickLine = (page, plan) =>
  page.getByText(new RegExp(`^Option \\d+ · ${escape(`${plan.carrier} ${plan.name}`)} · `));
const pageOf = (page, number) => page.getByRole('region', { name: new RegExp(`^Page ${number} of`) });

export const builder25 = {
  title: "The Proposal builder on GD1: each pick shows its own change, Pages' option numbers, a kept line needs no pick",
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec, base } = ctx;
    const [cg1, cg1n] = ['CG1', 'CG1N'].map((ref) => named(spec, ref));
    const written = [];
    let dealId;
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Advisor\'s "Proposal builder" pill opens the builder on Medical', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'Proposal builder' }).click();
      await page.getByText('What the client will see').waitFor();
      await page.getByRole('button', { name: /^Medical/ }).click();
      dealId = page.url().match(/\/deals\/(\d+)/)[1];
    });
    await step('the toolbar counts the cards and says nothing stops the proposal', async () => {
      await page.getByText(/✓ 0 of \d+ completed/).waitFor();
      if (await page.getByRole('status').filter({ hasText: 'A proposal always carries' }).count()) {
        throw new Error('GD1 reads not ready');
      }
    });
    let picks = [];
    await step(`${cg1.name} and ${cg1n.name} both answer for Current 1, each with its own change`, async () => {
      picks = [cg1, cg1n].map((plan) => pickLine(page, plan));
      const texts = await Promise.all(picks.map((pick) => pick.first().innerText()));
      if (!texts.every((text) => /replacing Current 1/.test(text) && /\/mo · [+−]?\d/.test(text))) {
        throw new Error(`the picks read ${JSON.stringify(texts)}`);
      }
      const changes = texts.map((text) => text.split(' · ').slice(-3, -1).join(' · '));
      if (changes[0] === changes[1]) throw new Error(`both show ${changes[0]}`);
    });
    await step("the picks' option numbers are the ones page 1 shows over their columns", async () => {
      const body = await api(page, base, `deals/${dealId}/proposal/pages/?line=medical&preset=key`);
      for (const plan of [cg1, cg1n]) {
        const column = body.plans.find((entry) => entry.name === plan.name);
        const words = await pickLine(page, plan).first().innerText();
        if (!words.startsWith(`Option ${column.option} ·`)) throw new Error(`${plan.name}: "${words}" vs ${column.option}`);
        await pageOf(page, 1).getByText(`Option ${column.option}`, { exact: true }).waitFor();
      }
    });
    await step('taking the vision renewal\'s recommendation away makes the banner name Vision', async () => {
      await page.getByRole('button', { name: /^Vision/ }).click();
      const answer = page.waitForResponse((response) => /\/recommend\/$/.test(new URL(response.url()).pathname));
      await page.getByRole('button', { name: '✓ Recommended' }).first().click();
      written.push((await (await answer).json()).activity_id);
      await page.getByRole('status').filter({ hasText: 'Pick a recommended plan before this goes to the client: Vision.' }).waitFor();
    });
    await step('kept as-is, Vision needs no pick: its incumbent card shows and the banner goes', async () => {
      const answer = await api(page, base, `deals/${dealId}/intake/intent/`, 'POST', {
        line: 'vision',
        has_today: true,
        this_year: 'keep',
      });
      written.push(answer.activity_id);
      await page.reload();
      await page.getByRole('button', { name: /^Vision/ }).click();
      await page.getByText('On the proposal, not in the market').waitFor();
      if (await page.getByRole('status').filter({ hasText: 'A proposal always carries' }).count()) {
        throw new Error('the kept line still blocks');
      }
    });
    await step('Revert puts the intent and the recommendation back', async () => {
      while (written.length) await api(page, base, `activity/${written.pop()}/revert/`, 'POST');
      await page.reload();
      await page.getByRole('button', { name: /^Vision/ }).click();
      await page.getByText('What the client will see').waitFor();
    });
    await step('"✓ Mark completed" on What this section shows collapses it and counts it; Undo takes it off', async () => {
      await page.getByRole('button', { name: '✓ Mark completed' }).last().click(); // the rows card is the last
      await page.getByText(/✓ 1 of \d+ completed/).waitFor();
      await page.getByRole('button', { name: 'Expand What this section shows' }).waitFor(); // collapsed
      await page.getByRole('button', { name: 'Undo' }).click();
      await page.getByText(/✓ 0 of \d+ completed/).waitFor();
    });
  },
};
