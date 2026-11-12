// Need 11 and slice 28's "done when" (plan.md §13.8 row 28; F3, F136, J27, J105, J107, J112, J116–J118): on GD1, the
// Advisor's Export viewer opens on the Excel chip, on the tab the file opens on; Ctrl+PgDn pages through every tab as
// the file shows it; Printed pages lays a tab on letter paper; a check jumps to its cell; "Open proposal ▸" on the
// builder opens the viewer; and none of it writes (the builder's files stamp, which moves with any recorded write,
// is the same after). Run with `--need 11`.

export const export28 = {
  title: 'The Export viewer on GD1: the Excel chip pages through every tab, and previews write nothing',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step } = ctx;
    const viewer = page.locator('[data-render]').filter({ has: page.getByRole('group', { name: 'Export' }) });
    const shownTab = () => viewer.getAttribute('data-viewer-tab');
    const ready = async (title) => {
      await page.waitForFunction(
        (want) => {
          const root = document.querySelector('.bnf-xw');
          return root?.dataset.render === 'ready' && (!want || root.dataset.viewerTab === want);
        },
        title,
        { timeout: 60000 },
      );
    };
    const stamp = () =>
      page.evaluate(async () => {
        const id = window.location.pathname.match(/\/deals\/(\d+)/)[1];
        const res = await fetch(`/api/deals/${id}/proposal/`, { credentials: 'same-origin' });
        return (await res.json()).stamps.files;
      });
    await signIn(ctx);
    await openDeal(ctx);
    let before = '';
    await step('the Advisor offers "Export viewer" as its last view pill', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('group', { name: 'View' }).getByRole('button', { name: 'Export viewer' }).waitFor();
      const pills = page.getByRole('group', { name: 'View' }).getByRole('button');
      const labels = await pills.allInnerTexts();
      if (labels.at(-1) !== 'Export viewer') throw new Error(labels.join(' | '));
      before = await stamp();
    });
    await step('it opens on the Excel chip, on the tab the file opens on, built', async () => {
      await page.getByRole('group', { name: 'View' }).getByRole('button', { name: 'Export viewer' }).click();
      await ready('Dynamic Medical Compare');
      const excel = page.getByRole('group', { name: 'Export' }).getByRole('button', { name: 'Excel' });
      if ((await excel.getAttribute('aria-pressed')) !== 'true') throw new Error('Excel is not picked');
      await page.getByRole('status').filter({ hasText: /^Built .+ · \d+ tabs$/ }).waitFor();
      if (!page.url().includes('view=export')) throw new Error(page.url());
    });
    const titles = await page.getByRole('tablist', { name: 'Tabs' }).getByRole('tab').allInnerTexts();
    await step(`Ctrl+PgDn pages through all ${titles.length} tabs, each drawn as a grid of the file's cells`, async () => {
      await page.getByRole('tab', { name: titles[0], exact: true }).click();
      await ready(titles[0]);
      for (const title of titles.slice(1)) {
        await viewer.focus();
        await page.keyboard.press('Control+PageDown');
        await ready(title);
        const cells = await viewer.locator('td[data-cell]').count();
        if (!cells) throw new Error(`${title}: no cells`);
      }
      if ((await shownTab()) !== titles.at(-1)) throw new Error(await shownTab());
    });
    await step('Printed pages lays a tab on letter paper, page by page', async () => {
      await page.getByRole('tab', { name: 'Dynamic Medical Compare', exact: true }).click();
      await ready('Dynamic Medical Compare');
      const look = page.getByRole('group', { name: 'How to look at it' });
      await look.getByRole('button', { name: 'Printed pages' }).click();
      await page.getByText(/^Prints on \d+ pages? at \d+%/).waitFor();
      await page.getByText(/^Page 1 of \d+$/).waitFor();
      await page.getByRole('button', { name: 'Next page' }).click();
      await page.getByText(/^Page 2 of \d+$/).waitFor();
      await look.getByRole('button', { name: 'Screen', exact: true }).click();
    });
    await step("a tab's check jumps to its cell (or the tab reports nothing to check)", async () => {
      await page.getByRole('tab', { name: 'Medical All Plans', exact: true }).click();
      await ready('Medical All Plans');
      const first = page.locator('.bnf-xw-check').first();
      if (await first.count()) {
        const cell = await first.locator('b').innerText();
        await first.click();
        await page.getByText(`Cell ${cell} selected.`, { exact: false }).waitFor();
      } else {
        await page.getByText('Medical All Plans: no formula errors').waitFor();
      }
    });
    await step('"Open proposal ▸" on the Proposal builder opens the Export viewer', async () => {
      await page.getByRole('group', { name: 'View' }).getByRole('button', { name: 'Proposal builder' }).click();
      await page.getByRole('button', { name: 'Open proposal ▸' }).click();
      await ready();
      if (!page.url().includes('view=export')) throw new Error(page.url());
    });
    await step('nothing was written: the files stamp is unchanged', async () => {
      const after = await stamp();
      if (after !== before) throw new Error(`${before} → ${after}`);
    });
  },
};
