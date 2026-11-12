// Slice 14's "done when" (plan.md §13 row 14; F37–F39, F45, F46, F52, J5–J13; needs 8 and 9): on GD1's ▦ Pages,
// "What the client will see", clicking a column name and picking a plan puts it in that slot with the slot's star and
// link; the plan picked over loses its recommendation; "Replacing:" groups a quote under its plan, and "Several…"
// makes a consolidation. Run with `--need 9` (picks) and `--need 8` (Replacing:). Each starts from GD1 as seeded and
// undoes each write right after checking it (POST activity/{id}/revert/), so GD1 is left as it found it.

async function api(page, base, url, method = 'GET') {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
  const response = await page.request.fetch(`${base}/api/${url}`, {
    method,
    headers: { 'X-CSRFToken': csrf, Referer: base },
  });
  if (!response.ok()) throw new Error(`${method} ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

// The Activity rows the walk's own writes (a pick, a link) answer with, so the last step can put GD1 back.
function recordWrites(page) {
  const rows = [];
  page.on('response', async (response) => {
    const path = new URL(response.url()).pathname;
    if (response.request().method() !== 'POST' || !/\/plans\/(slot|links)\/$/.test(path)) return;
    const body = await response.json().catch(() => null);
    if (body?.activity_id) rows.push(body.activity_id);
  });
  return rows;
}

const pageOf = (page, number) => page.getByRole('region', { name: new RegExp(`^Page ${number} of`) });
const named = (spec, ref) => spec.plans.find((plan) => plan.ref === ref);
// A column's name: the button that opens the picker reads the carrier, then the plan.
const nameOf = (where, plan) => where.getByRole('button', { name: new RegExp(`^${plan.carrier}\\s*${plan.name}$`) });

// Medical's ▦ Pages on GD1.
async function openPages(ctx, { signIn, openDeal }) {
  const { page, step } = ctx;
  await signIn(ctx);
  await openDeal(ctx);
  await step('the Advisor opens on the medical board', async () => {
    await page.getByRole('link', { name: 'Advisor', exact: true }).click();
    await page.getByRole('button', { name: /^Medical/ }).click();
    await page.getByRole('button', { name: '▦ Pages' }).waitFor();
  });
  await step('▦ Pages shows "What the client will see": a page per current plan, the first one full', async () => {
    await page.getByRole('button', { name: '▦ Pages' }).click();
    await pageOf(page, 1).getByText('6 of 6 columns · full').waitFor();
    await pageOf(page, 2).getByText('Replacing: Aetna Choice POS II PPO 1500').waitFor();
  });
  return page.url().match(/\/deals\/(\d+)/)[1];
}

// Revert keeps to the latest write on a key, so each check undoes its own write before the next one.
async function undo(ctx, rows, what) {
  const { page, step, base } = ctx;
  await step(`Revert puts ${what} back, so GD1 is as it was`, async () => {
    const id = rows.pop();
    if (!id) throw new Error('the write answered no Activity row');
    await api(page, base, `activity/${id}/revert/`, 'POST');
    await page.reload();
    await pageOf(page, 1).getByText('6 of 6 columns · full').waitFor();
  });
}

export const pages14 = {
  9: {
    title: 'Click a plan into a chosen slot (F45, J10, D-222): on GD1 the pick takes the slot’s place, star and link',
    deal: 'GD1',
    async run(ctx, helpers) {
      const { page, step, spec, base } = ctx;
      const rows = recordWrites(page);
      const dealId = await openPages(ctx, helpers);
      const [cg1, cg2, cg3] = ['CG1', 'CG2', 'CG3'].map((ref) => named(spec, ref));
      const plans = async () => (await api(page, base, `deals/${dealId}/plans/?line=medical`)).plans;
      await step(`clicking ${cg3.name} on page 2 opens the picker: the proposal first, then the other quotes`, async () => {
        await nameOf(pageOf(page, 2), cg3).click();
        const picker = page.getByRole('dialog', { name: `Change ${cg3.name}` });
        await picker.getByText('On the proposal', { exact: true }).waitFor();
        await picker.getByText('Other scanned quotes', { exact: true }).waitFor();
      });
      await step(`typing "3500" narrows it to ${cg2.name}, which Enter picks`, async () => {
        const picker = page.getByRole('dialog', { name: `Change ${cg3.name}` });
        await picker.getByRole('combobox').fill('3500');
        await picker.getByRole('option', { name: new RegExp(cg2.name) }).waitFor();
        await picker.getByRole('combobox').press('Enter');
        await picker.waitFor({ state: 'detached' });
      });
      await step(`${cg2.name} takes ${cg3.name}’s place on page 2, with its star and its link`, async () => {
        const heads = pageOf(page, 2).getByRole('columnheader');
        await heads.nth(2).getByText(cg2.name).waitFor(); // Column, then B, then the slot
        const now = await plans();
        const b = now.find((plan) => plan.name === named(spec, 'B').name && plan.role === 'current');
        const picked = now.find((plan) => plan.name === cg2.name);
        if (!picked.starred || JSON.stringify(picked.replaces_ids) !== JSON.stringify([b.id])) {
          throw new Error(`${cg2.name}: starred ${picked.starred}, replaces ${picked.replaces_ids}`);
        }
        if (now.find((plan) => plan.name === cg3.name).starred) throw new Error(`${cg3.name} kept its star`);
      });
      await undo(ctx, rows, 'the pick');
      await step(`picking ${cg2.name} over the recommended ${cg1.name} takes its recommendation away`, async () => {
        await nameOf(pageOf(page, 1), cg1).click();
        const picker = page.getByRole('dialog', { name: `Change ${cg1.name}` });
        await picker.getByRole('combobox').fill(cg2.name);
        await picker.getByRole('option', { name: new RegExp(cg2.name) }).click();
        await picker.waitFor({ state: 'detached' });
        await nameOf(pageOf(page, 1), cg2).waitFor();
        const left = (await plans()).find((plan) => plan.name === cg1.name);
        if (left.recommended || left.starred) throw new Error(`${cg1.name} kept its pick`);
      });
      await undo(ctx, rows, 'the pick and the recommendation');
    },
  },
  8: {
    title: 'Which quote replaces which plan (F52, J12): "Replacing:" groups a quote under its plan; "Several…" consolidates',
    deal: 'GD1',
    async run(ctx, helpers) {
      const { page, step, spec } = ctx;
      const rows = recordWrites(page);
      await openPages(ctx, helpers);
      const [cg3, cg4] = ['CG3', 'CG4'].map((ref) => named(spec, ref));
      const picker = (number, plan) =>
        pageOf(page, number).getByRole('combobox', { name: `Which current plan ${plan.name} replaces` });
      await step(`"Replacing: Current 3" moves ${cg3.name} from page 2 to page 3`, async () => {
        await picker(2, cg3).selectOption({ index: 3 }); // Pick a current plan, Current 1, 2, 3
        await nameOf(pageOf(page, 3), cg3).waitFor();
        if (await nameOf(pageOf(page, 2), cg3).count()) {
          throw new Error(`${cg3.name} is still on page 2`);
        }
      });
      await undo(ctx, rows, 'the link');
      await step(`"Several…" ticks Current 2 and Current 3 for ${cg4.name}: a consolidation, under Current 2`, async () => {
        await picker(3, cg4).selectOption({ label: 'Several…' });
        const group = page.getByRole('group', { name: `The current plans ${cg4.name} replaces` });
        await group.getByRole('checkbox', { name: /^Current 2/ }).check();
        await group.getByRole('checkbox', { name: /^Current 3/ }).check();
        await group.getByRole('button', { name: 'Replace these 2' }).click();
        await picker(2, cg4).waitFor();
        const shown = await picker(2, cg4).evaluate((select) => select.options[select.selectedIndex].text);
        if (shown !== 'Several: Current 2 + 3') throw new Error(`the picker reads "${shown}"`);
      });
      await undo(ctx, rows, 'the consolidation');
    },
  },
};
