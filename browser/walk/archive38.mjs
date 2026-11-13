// Slice 38's "done when" (plan.md §13.9 row 38; A13, A18, M6–M9, M77, M103–M105, J22): a deal opened for an Existing
// client shows RENEWAL in the Proposal builder (GD1's does not); archiving the client hides it everywhere and Restore
// brings it back; deleting a pinned note can be undone. Run with `--need s38`.
//
// It works on its own synthetic client, "Walk 38 Renewal Co. (synthetic)", made through the New client dialog the first
// time and reused after; it ends archived, so the lists stay as they were. GD1 is only read.

const WALK_CLIENT = 'Walk 38 Renewal Co. (synthetic)';

async function api(page, base, url, method = 'GET', body = undefined) {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
  const response = await page.request.fetch(`${base}/api/${url}`, {
    method,
    headers: { 'X-CSRFToken': csrf, Referer: base, 'Content-Type': 'application/json' },
    data: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok()) throw new Error(`${method} ${url} answered ${response.status()}: ${await response.text()}`);
  return response.status() === 204 ? null : response.json();
}

const listed = async (page, base, q) =>
  (await api(page, base, `clients/?q=${encodeURIComponent(q)}`)).results.filter((row) => row.name === q);

const openBuilder = async (page) => {
  await page.getByRole('link', { name: 'Advisor', exact: true }).click();
  await page.getByRole('button', { name: 'Proposal builder' }).click();
  await page.getByText(/✓ \d+ of \d+ completed/).waitFor();
};

export const archive38 = {
  title: 'RENEWAL on an Existing client\'s builder; Archive hides a client everywhere and Restore brings it back; a ' +
    "deleted pinned note's Undo",
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base } = ctx;
    let clientId;
    let dealId;
    await signIn(ctx);

    await step("GD1, a prospect's deal, shows no RENEWAL chip in its builder", async () => {
      await openDeal(ctx);
      await openBuilder(page);
      if (await page.getByText('RENEWAL', { exact: true }).count()) throw new Error('GD1 shows RENEWAL');
    });

    await step(`"${WALK_CLIENT}" is an Existing client (made through ＋ New client the first time)`, async () => {
      const archived = (await api(page, base, 'archived/')).find((row) => row.name === WALK_CLIENT);
      if (archived) await api(page, base, `clients/${archived.id}/archive/`, 'POST', { archived: false });
      const found = (await listed(page, base, WALK_CLIENT))[0];
      if (found) {
        [clientId, dealId] = [found.id, found.deal.id];
        await page.goto(`${base}/deals/${dealId}/advisor`);
      } else {
        await page.goto(`${base}/?view=book`);
        await page.getByRole('button', { name: /New client/ }).click();
        const dialog = page.getByRole('dialog');
        await dialog.getByLabel('Client name').fill(WALK_CLIENT);
        await dialog.getByLabel('Status').selectOption({ label: 'Existing client' });
        await dialog.getByRole('button', { name: 'Create' }).click();
        await page.waitForURL(/\/deals\/\d+/);
        dealId = page.url().match(/\/deals\/(\d+)/)[1];
        clientId = (await api(page, base, `deals/${dealId}/`)).client.id;
      }
      const header = await api(page, base, `deals/${dealId}/`);
      if (header.client.relationship !== 'existing_client') throw new Error(`status ${header.client.relationship}`);
    });

    await step('with last year\'s plan on the deal, the Proposal builder leads with RENEWAL', async () => {
      const plans = await api(page, base, `deals/${dealId}/plans/?line=medical`);
      if (!plans.plans.some((plan) => plan.role === 'current')) {
        const plan = { line: 'medical', role: 'current', carrier: 'Cigna', name: 'Walk 38 Open Access Plus' };
        await api(page, base, `deals/${dealId}/plans/`, 'POST', plan);
      }
      await page.goto(`${base}/deals/${dealId}/advisor`);
      await openBuilder(page);
      await page.getByText('RENEWAL', { exact: true }).waitFor();
    });

    await step('Archive… asks first, naming the client, then the header says it is off every list', async () => {
      await page.goto(`${base}/deals/${dealId}/overview`); // Archive… lives on the Overview from slice 62 (M1, M112)
      await page.getByRole('button', { name: 'Archive…' }).click();
      await page.getByText(`Archive ${WALK_CLIENT}?`).waitFor();
      await page.getByRole('group', { name: 'Archive this client' }).getByRole('button', { name: 'Archive' }).click();
      await page.getByRole('status').filter({ hasText: /Archived .* off every list\. Nothing was deleted\./ }).waitFor();
    });

    await step('the client is on neither home list, nor found by search', async () => {
      for (const view of ['/', '/?view=book']) {
        await page.goto(`${base}${view}`);
        await page.getByLabel(/search clients/i).fill('Walk 38');
        await page.waitForTimeout(600); // the search waits for typing to stop
        await page.getByRole('heading', { level: 1 }).waitFor();
        if (await page.getByRole('link', { name: WALK_CLIENT }).count()) throw new Error(`still listed on ${view}`);
      }
      if ((await listed(page, base, WALK_CLIENT)).length) throw new Error('GET clients/ still lists it');
    });

    await step('Archived lists it with its status, Existing client, and Restore', async () => {
      await page.getByRole('link', { name: 'Archived', exact: true }).first().click();
      await page.waitForURL(/\/archived$/);
      const row = page.getByRole('row', { name: new RegExp(WALK_CLIENT.replace(/[().]/g, '\\$&')) });
      await row.getByText('Existing client').waitFor();
      await row.getByRole('button', { name: `Restore ${WALK_CLIENT}` }).click();
      await row.waitFor({ state: 'detached' });
    });

    await step('Restore brings it back: Clients finds it again', async () => {
      await page.goto(`${base}/?view=book`);
      await page.getByLabel(/search clients/i).fill('Walk 38');
      await page.getByRole('link', { name: WALK_CLIENT }).first().waitFor();
    });

    let note;
    await step('a pinned note, deleted, leaves the notes; the Activity drawer offers its Revert', async () => {
      note = await api(page, base, `deals/${dealId}/notes/`, 'POST', {
        body: 'Walk 38: called the HR lead about the renewal.',
        kind: 'call',
        pinned: true,
      });
      await api(page, base, `notes/${note.id}/`, 'DELETE');
      if ((await api(page, base, `deals/${dealId}/notes/`)).some((row) => row.id === note.id)) {
        throw new Error('the deleted note is still listed');
      }
      await page.goto(`${base}/deals/${dealId}/advisor`);
      await page.getByRole('button', { name: 'Activity', exact: true }).click();
      await page.getByText('Deleted a pinned note').first().waitFor();
    });

    await step('Revert brings the note back, still pinned', async () => {
      const entry = page.locator('li').filter({ has: page.getByText('Deleted a pinned note', { exact: true }) }).first();
      await entry.getByRole('button', { name: 'Revert this change' }).click();
      await entry.getByText(/^Reverted by/).waitFor();
      const back = (await api(page, base, `deals/${dealId}/notes/`)).find((row) => row.id === note.id);
      if (!back?.pinned) throw new Error(`the note came back as ${JSON.stringify(back)}`);
    });

    await step('the walk leaves its client archived again, so the lists are as they were', async () => {
      await api(page, base, `clients/${clientId}/archive/`, 'POST', { archived: true });
    });
  },
};
