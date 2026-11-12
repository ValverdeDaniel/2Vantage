// Slice 31's "done when" (plan.md §13.8 row 31; J24, J141): on GD1's Proposal builder, "⬇ PowerPoint" sits beside
// "⬇ Client PDF" and downloads the client PowerPoint under the server's file name: the old master with its four
// layouts, a native chart, speaker notes, a slide for each of the PDF's pages (the backend tests replay every frame:
// proposals/tests/test_client_pptx.py). Run with `--need s31`. It writes nothing but the download's "downloaded" row.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// A .pptx is a zip: its central directory names every part in plain text, so the parts can be counted unopened.
function parts(file, pattern) {
  const text = fs.readFileSync(file).toString('latin1');
  return new Set(text.match(pattern) ?? []);
}

export const pptx31 = {
  title: 'The Proposal builder on GD1: ⬇ PowerPoint downloads the deck as slides, with the master, a chart and notes',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Advisor\'s "Proposal builder" has "⬇ PowerPoint" beside "⬇ Client PDF"', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'Proposal builder' }).click();
      await page.getByRole('button', { name: '⬇ PowerPoint' }).waitFor();
      const names = await page.locator('.bnf-build-toolbar button').allInnerTexts();
      const pdf = names.findIndex((name) => name.includes('Client PDF'));
      if (pdf < 0 || !names[pdf + 1]?.includes('PowerPoint')) throw new Error(names.join(' | '));
    });
    let file = '';
    await step('the button downloads the PowerPoint under the server\'s name', async () => {
      const download = page.waitForEvent('download', { timeout: 60000 });
      await page.getByRole('button', { name: '⬇ PowerPoint' }).click();
      const got = await download;
      // J104: the client spreadsheet's name rule (slice 28), the effective date's year, Draft until issued.
      const year = spec.effective_date.slice(0, 4);
      const safe = `${spec.client} - ${year} Benefits Proposal-DRAFT.pptx`.replace(/[^A-Za-z0-9 ._-]/g, '');
      if (got.suggestedFilename() !== safe) throw new Error(got.suggestedFilename());
      file = path.join(os.tmpdir(), `walk-s31-${Date.now()}.pptx`);
      await got.saveAs(file);
    });
    await step('the file is a deck: one master, four layouts, more slides than a cover and a closing', async () => {
      if (fs.readFileSync(file).subarray(0, 2).toString('latin1') !== 'PK') throw new Error('not a .pptx');
      const masters = parts(file, /ppt\/slideMasters\/slideMaster\d+\.xml(?!\.rels)/g);
      const layouts = parts(file, /ppt\/slideLayouts\/slideLayout\d+\.xml(?!\.rels)/g);
      const slides = parts(file, /ppt\/slides\/slide\d+\.xml(?!\.rels)/g);
      if (masters.size !== 1 || layouts.size !== 4) throw new Error(`${masters.size} masters, ${layouts.size} layouts`);
      if (slides.size < 6) throw new Error(`${slides.size} slides`);
    });
    await step('the premium chart is a native chart and the slides carry speaker notes', async () => {
      if (!parts(file, /ppt\/charts\/chart\d+\.xml/g).size) throw new Error('no native chart');
      if (!parts(file, /ppt\/notesSlides\/notesSlide\d+\.xml/g).size) throw new Error('no speaker notes');
    });
    await step('the button is free again once the file is saved', async () => {
      const button = page.getByRole('button', { name: '⬇ PowerPoint' });
      if (await button.getAttribute('aria-busy')) throw new Error('still busy');
    });
  },
};
