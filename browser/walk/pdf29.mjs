// Slice 29's "done when" (plan.md §13.8 row 29; J24, J122–J140): on GD1's Proposal builder, "⬇ Client PDF" downloads
// the client PDF: a 16:9 deck under the server's file name, one page a slide, the old Presentation pages (the backend
// tests read its words: proposals/tests/test_client_pdf.py). Run with `--need s29`. It writes nothing but the
// download's own "downloaded" row.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const pdf29 = {
  title: 'The Proposal builder on GD1: ⬇ Client PDF downloads the 16:9 Presentation deck',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Advisor\'s "Proposal builder" opens with "⬇ Client PDF" on its toolbar', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'Proposal builder' }).click();
      await page.getByRole('button', { name: '⬇ Client PDF' }).waitFor();
    });
    let file = '';
    await step('the button downloads the PDF under the server\'s name', async () => {
      const download = page.waitForEvent('download', { timeout: 60000 });
      await page.getByRole('button', { name: '⬇ Client PDF' }).click();
      const got = await download;
      const safe = `${spec.client} - Proposal.pdf`.replace(/[^A-Za-z0-9 ._-]/g, ''); // deals.downloads.safe_filename
      if (got.suggestedFilename() !== safe) throw new Error(got.suggestedFilename());
      file = path.join(os.tmpdir(), `walk-s29-${Date.now()}.pdf`);
      await got.saveAs(file);
    });
    await step('the file is a PDF of 16:9 pages (960 × 540 pt), more than a cover and a closing', async () => {
      const text = fs.readFileSync(file).toString('latin1');
      if (!text.startsWith('%PDF-')) throw new Error('not a PDF');
      const pages = text.match(/\/Type \/Page\b/g) ?? [];
      if (pages.length < 6) throw new Error(`${pages.length} pages`);
      if (!/\/MediaBox \[ 0 0 960 540 \]/.test(text)) throw new Error('the pages are not 960 × 540');
    });
    await step('the button is free again once the file is saved', async () => {
      const button = page.getByRole('button', { name: '⬇ Client PDF' });
      if (await button.getAttribute('aria-busy')) throw new Error('still busy');
    });
  },
};
