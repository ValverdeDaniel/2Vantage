// Slice 64's "done when" (plan.md §13.10 row 64; Q.9 row 64; M83–M93): Confirm all for one document can be undone.
// On GD1's Overview, Data confidence stands last among the side cards, after Commission, with review's own counts:
// Scanned (its values typed from the deal's files: "corrected by hand"), Typed, From the client, the Confirmed bar and
// each file's quality and "N values · 0 confirmed". Confirm all on the Cigna quote asks "Confirm N values from this
// file?", then every value read from the file is approved on its owner as one review (one Activity row of marks) and
// the file reads "N values · N confirmed"; the toast's Undo reverts that one row and every value is back unconfirmed.
// The AI re-read offers Double-check with AI; the walk never presses it (no Claude call). Run with `--need s64` on a
// fresh GD1 (`manage.py seed_golden GD1`); it leaves the marks as they were, but seed GD1 again afterwards (its
// Activity holds the review and its revert).

const FILE = 'Cigna medical quote (synthetic).xlsx';

async function api(page, base, url) {
  const response = await page.request.fetch(`${base}/api/${url}`);
  if (!response.ok()) throw new Error(`GET ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

const tab = (page) => page.getByRole('region', { name: 'Overview' });
const top = async (locator) => (await locator.first().boundingBox()).y;

export const confidence64 = {
  title: 'Slice 64: Data confidence on the Overview — Confirm all for one document, then Undo (M83–M93)',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base } = ctx;
    let dealId;
    let before;
    let file;
    await signIn(ctx);
    await openDeal(ctx);

    await step('Data confidence stands last among the side cards, under Commission (the old order)', async () => {
      await page.waitForURL(/\/deals\/\d+\/overview/);
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      const card = tab(page).getByText('Data confidence', { exact: true });
      await card.waitFor({ timeout: 20000 });
      const commission = tab(page).getByText('Commission', { exact: true }).first();
      if ((await top(card)) <= (await top(commission))) throw new Error('Data confidence stands above Commission');
      await tab(page).getByText('Where each value came from, and whether it has been checked.').waitFor();
    });

    await step('its cells, bar and files are review’s counts: Scanned, Typed, From the client, 0 confirmed (M83, M86)', async () => {
      before = await api(page, base, `deals/${dealId}/confidence/`);
      file = before.documents.find((doc) => doc.name === FILE);
      if (!file || file.values < 1 || file.confirmed !== 0) throw new Error(`the Cigna file reads ${JSON.stringify(file)}`);
      if (before.cells.scanned < file.values) throw new Error('the scanned cell counts fewer values than the file');
      const region = tab(page);
      await region.getByText(`${before.cells.corrected} corrected by hand`, { exact: true }).waitFor();
      await region.getByText(`${before.confirmed.total}/${before.filled} · ${before.confirmed.pct}%`).waitFor();
      await region.getByText(`${file.values} values · 0 confirmed`, { exact: true }).waitFor();
      await region.getByRole('button', { name: 'Double-check with AI' }).waitFor();
    });

    const row = () => tab(page).locator('.bnf-ov-conf-doc').filter({ hasText: FILE });

    await step('Confirm all asks first: "Confirm N values from this file?" (M88)', async () => {
      await row().getByRole('button', { name: 'Confirm all' }).click();
      await page.getByRole('dialog').getByText(`Confirm ${file.values} values from this file?`).waitFor();
    });

    await step('confirming marks every value of the file as one review: "N values · N confirmed", the bar moves', async () => {
      await page.getByRole('dialog').getByRole('button', { name: 'Confirm all' }).click();
      await page.locator('.bb-toast').getByText(`Confirmed ${file.values} values`).waitFor();
      await row().getByText(`${file.values} values · ${file.values} confirmed`, { exact: true }).waitFor();
      if (await row().getByRole('button', { name: 'Confirm all' }).count()) throw new Error('Confirm all is still offered');
      const bar = `${before.confirmed.total + file.values}/${before.filled} · `;
      await tab(page).getByText(bar).waitFor();
    });

    await step('the toast’s Undo puts every value back unconfirmed, and Confirm all is offered again (M88)', async () => {
      await page.locator('.bb-toast').getByRole('button', { name: 'Undo' }).click(); // before the toast's 10 s run out
      await page.locator('.bb-toast').getByText(`Undone — ${file.values} values back as before`).waitFor();
      await row().getByText(`${file.values} values · 0 confirmed`, { exact: true }).waitFor();
      await row().getByRole('button', { name: 'Confirm all' }).waitFor();
    });

    await step('it was one Activity row of marks, reverted once: the counts are back and a second Undo is refused', async () => {
      const after = await api(page, base, `deals/${dealId}/confidence/`);
      if (after.confirmed.total !== before.confirmed.total) throw new Error('the bar did not come back');
      const feed = await api(page, base, `deals/${dealId}/activity/`);
      const rows = feed.results || feed;
      const review = rows.find((entry) => entry.action === 'marked' && entry.area === 'review');
      if (!review || review.summary !== `Approved ${file.values} values from one file` || !review.reverted) {
        throw new Error(`no reverted review row: ${JSON.stringify(rows.slice(0, 3))}`);
      }
      if (!rows.some((entry) => entry.action === 'reverted' && entry.reverts_id === review.id)) {
        throw new Error('no revert row for the review');
      }
      const again = await page.request.fetch(`${base}/api/activity/${review.id}/revert/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': (await page.context().cookies()).find((c) => c.name === 'csrftoken')?.value || '' },
      });
      if (again.status() !== 409) throw new Error(`a second Undo answered ${again.status()}, not 409`);
    });
  },
};
