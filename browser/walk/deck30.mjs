// Need 11's deck files and slice 30's "done when" (plan.md §13.8 row 30; J108–J111, J114, J115, J58): on GD1, the
// Export viewer's PowerPoint chip opens on the first Medical plan set with its fit report and speaker notes and pages
// through every slide by the keys; PDF keeps the same page and copy (no second build) and pages through; Paper shows
// each page on its US Letter sheet (11 × 8.5, the page at 75%) and says the table's printed type; Print… opens its
// window on the click and calls the print dialog there (headless Chrome shows none, so the walk records the call);
// "See the slides ▸" on the builder opens the PowerPoint on that line's first plan set; and none of it writes (the
// files stamp). Run with `--need 11d`.

export const deck30 = {
  title: 'The Export viewer on GD1: PowerPoint, PDF and Paper page through the slides; Print… opens the print dialog',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step } = ctx;
    const deck = page.locator('[data-viewer-file]');
    const chip = (name) => page.getByRole('group', { name: 'Export' }).getByRole('button', { name, exact: true });
    const ready = (file, n) =>
      page.waitForFunction(
        ([want, at]) => {
          const root = document.querySelector('[data-viewer-file]');
          return (
            root?.dataset.render === 'ready' &&
            root.dataset.viewerFile === want &&
            (!at || root.dataset.viewerPage === String(at))
          );
        },
        [file, n],
        { timeout: 60000 },
      );
    const shown = async () => Number(await deck.getAttribute('data-viewer-page'));
    const stamp = () =>
      page.evaluate(async () => {
        const id = window.location.pathname.match(/\/deals\/(\d+)/)[1];
        const res = await fetch(`/api/deals/${id}/proposal/`, { credentials: 'same-origin' });
        return (await res.json()).stamps.files;
      });
    let builds = 0;
    page.on('request', (req) => {
      if (/\/proposal\/preview\/\?.*file=deck/.test(req.url())) builds += 1;
    });
    // Headless Chrome has no print dialog: every page records a print() call instead.
    await page.context().addInitScript(() => {
      window.print = () => {
        window.localStorage.setItem('walk.printed', String(Date.now()));
      };
    });

    await signIn(ctx);
    await openDeal(ctx);
    let before = '';
    let count = 0;
    let first = 0;
    await step('the PowerPoint chip is live and opens on the first Medical plan set, built', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('group', { name: 'View' }).getByRole('button', { name: 'Export viewer' }).click();
      before = await stamp();
      await chip('PowerPoint').click();
      await ready('powerpoint');
      const status = await page.getByRole('status').filter({ hasText: /^Built .+ · \d+ slides$/ }).innerText();
      count = Number(status.match(/(\d+) slides$/)[1]);
      first = await shown();
      await page.getByText(new RegExp(`^Slide ${first} of ${count} · Medical — `)).waitFor();
      if (!page.url().includes('file=powerpoint')) throw new Error(page.url());
    });
    await step('the plan set shows its fit report, its speaker notes, and Jump chips for every plan set', async () => {
      await page.locator('.bnf-xv-fit').getByText(/^Fits on one slide at [\d.]+ pt/).waitFor();
      await page.getByText('Speaker notes', { exact: true }).waitFor();
      const jumps = await page.getByRole('group', { name: 'Jump to' }).getByRole('button').count();
      if (jumps < 2) throw new Error(`${jumps} jump chips`);
      const thumbs = await page.locator('.bnf-xv-rail button').count();
      if (thumbs !== count) throw new Error(`${thumbs} thumbnails for ${count} slides`);
    });
    await step(`Home, then → pages through all the slides one by one, and End lands on the last`, async () => {
      await deck.focus();
      await page.keyboard.press('Home');
      await ready('powerpoint', 1);
      for (let n = 2; n <= count; n += 1) {
        await page.keyboard.press('ArrowRight');
        await ready('powerpoint', n);
      }
      await page.keyboard.press('Home');
      await ready('powerpoint', 1);
      await page.keyboard.press('End');
      await ready('powerpoint', count);
    });
    await step('a Jump chip goes straight back to its plan set', async () => {
      await page.getByRole('group', { name: 'Jump to' }).getByRole('button').first().click();
      await ready('powerpoint', first);
    });
    await step('the PDF chip keeps the same page and copy, with no speaker notes, and PgDn/PgUp page through', async () => {
      const builtBefore = builds;
      await chip('PDF').click();
      await ready('pdf', first);
      await page.getByText(new RegExp(`^Page ${first} of ${count} · `)).waitFor();
      if (await page.getByText('Speaker notes', { exact: true }).count()) throw new Error('the PDF shows notes');
      await deck.focus();
      await page.keyboard.press('PageDown');
      await ready('pdf', first + 1);
      await page.keyboard.press('PageUp');
      await ready('pdf', first);
      if (builds !== builtBefore) throw new Error(`${builds - builtBefore} new builds`);
    });
    await step('Paper shows the page on its US Letter sheet (11 × 8.5) at 75%, with the printed type', async () => {
      await chip('Paper').click();
      await ready('paper', first);
      await page.getByText(/^Prints on US Letter landscape at 75%, inside a half-inch margin\. This table’s [\d.]+ pt type prints at [\d.]+ pt\.$/).waitFor();
      const frame = await page.locator('[data-frame="paper"]').boundingBox();
      const canvas = await page.locator('[data-frame="paper"] canvas').boundingBox();
      const sheet = frame.width / frame.height;
      const share = canvas.width / frame.width;
      if (Math.abs(sheet - 11 / 8.5) > 0.01) throw new Error(`sheet ${sheet.toFixed(3)}`);
      if (Math.abs(share - 720 / 792) > 0.01) throw new Error(`page share ${share.toFixed(3)}`);
    });
    await step('Print… opens its window on the click, shows the Letter PDF there and opens the print dialog', async () => {
      const popup = page.context().waitForEvent('page', { timeout: 30000 });
      await page.getByRole('button', { name: 'Print…' }).click();
      const win = await popup;
      await win.waitForURL(/^blob:/, { timeout: 60000 });
      await win.waitForFunction(() => window.localStorage.getItem('walk.printed'), null, { timeout: 30000 });
      await win.close();
    });
    await step('"See the slides ▸" on the builder opens the PowerPoint on that line\'s first plan set', async () => {
      await page.getByRole('group', { name: 'View' }).getByRole('button', { name: 'Proposal builder' }).click();
      await page.getByRole('button', { name: 'See the slides ▸' }).click();
      await ready('powerpoint', first);
      if (!/view=export/.test(page.url()) || !/file=powerpoint/.test(page.url())) throw new Error(page.url());
    });
    await step('nothing was written: the files stamp is unchanged', async () => {
      const after = await stamp();
      if (after !== before) throw new Error(`${before} → ${after}`);
    });
  },
};
