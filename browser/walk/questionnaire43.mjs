// Slice 43's "done when" (plan.md §13.9 row 43; G56, G61–G67, G135): on GD6 the ⬇ menu offers the filled form and
// the carrier's blank; "Download PDF" shows the check first, and a check gone stale while it was open is refused and
// shown again; the officer's signature files the signed copy in Documents, where Remove is refused; the signed copy
// downloads under the server's name. That stamped values sit inside their boxes is pinned by the backend tests
// (questionnaire/tests/test_stamp.py). Run with `--need s43` on a freshly seeded GD6 (`seed_golden GD6`); it leaves
// GD6's questionnaire signed and its signed copy filed, so seed it again afterwards.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const slug = (text) =>
  text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');

async function pick(page, item) {
  await page.getByRole('button', { name: '⬇ Download ▾' }).click();
  await page.getByRole('menuitem', { name: new RegExp(`^${item}`) }).click();
}

async function saved(download, name) {
  const got = await download;
  if (got.suggestedFilename() !== name) throw new Error(`the file is named ${got.suggestedFilename()}`);
  const file = path.join(os.tmpdir(), `walk-s43-${Date.now()}-${name}`);
  await got.saveAs(file);
  if (!fs.readFileSync(file).toString('latin1').startsWith('%PDF-')) throw new Error('not a PDF');
}

export const questionnaire43 = {
  title: 'Slice 43: the ⬇ menu and its check on GD6; a stale check is refused; the signed copy is filed and kept',
  deal: 'GD6',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const officer = spec.get_to_market.contacts[0].name;
    const filed = `${slug(spec.client)}-medical-questionnaire.pdf`;
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Questionnaire tab shows "⬇ Download ▾" and "Check the form ▸" on its toolbar', async () => {
      await page.getByRole('link', { name: 'Questionnaire', exact: true }).click();
      await page.getByRole('heading', { name: 'Florida Blue Underwriting Questionnaire' }).waitFor();
      await page.getByRole('button', { name: 'Check the form ▸' }).waitFor();
    });
    await step('the menu offers "Download PDF" and "Blank carrier PDF", each saying what it is', async () => {
      await page.getByRole('button', { name: '⬇ Download ▾' }).click();
      const items = page.getByRole('menuitem');
      const names = await items.allInnerTexts();
      if (names.length !== 2) throw new Error(`the menu has ${names.join(' | ')}`);
      if (!/^Download PDF/.test(names[0]) || !/marked DRAFT until it is signed/.test(names[0])) throw new Error(names[0]);
      if (!/^Blank carrier PDF/.test(names[1])) throw new Error(names[1]);
      await page.keyboard.press('Escape');
    });
    await step('"Blank carrier PDF" downloads the carrier\'s empty form as florida-blue-51-blank.pdf', async () => {
      const download = page.waitForEvent('download', { timeout: 60000 });
      await pick(page, 'Blank carrier PDF');
      await saved(download, 'florida-blue-51-blank.pdf');
    });
    await step('"Check the form ▸" shows the filled PDF beside what is wrong with it', async () => {
      await page.getByRole('button', { name: 'Check the form ▸' }).click();
      await page.getByText('The filled PDF as it will download, beside what is wrong with it.').waitFor();
      await page.getByText('Florida Blue Underwriting Questionnaire has not been started.').first().waitFor();
      await page.locator('canvas').first().waitFor({ timeout: 60000 });
      await page.getByRole('button', { name: 'Hide the form' }).click();
    });
    await step('"Download PDF" opens "Before you download" with what is wrong, and nothing goes out yet', async () => {
      await pick(page, 'Download PDF');
      const dialog = page.getByRole('dialog', { name: 'Before you download' });
      await dialog.getByText('Before you download: Florida Blue Underwriting Questionnaire').waitFor();
      await dialog.getByText('Florida Blue Underwriting Questionnaire has not been started.').waitFor();
      await dialog.getByRole('button', { name: 'Download anyway ⬇' }).waitFor();
    });
    await step('someone answers a question in another tab: the download is refused and the fresh check shows', async () => {
      const other = await page.context().newPage();
      await other.goto(page.url());
      await other.getByLabel(/^10\. Has this group had Florida Blue/).selectOption('No');
      await other.getByText('Saving…').waitFor({ state: 'detached' });
      await other.waitForTimeout(1500);
      await other.close();
      const dialog = page.getByRole('dialog', { name: 'Before you download' });
      await dialog.getByRole('button', { name: 'Download anyway ⬇' }).click();
      await dialog.getByText('Something changed since you opened this. Here is the check as it stands now.').waitFor();
      await dialog.getByText(/required answers? on Florida Blue Underwriting Questionnaire (is|are) still blank/).waitFor();
    });
    await step(`"Download anyway ⬇" on the fresh check downloads the draft as ${filed}`, async () => {
      const download = page.waitForEvent('download', { timeout: 60000 });
      await page.getByRole('dialog').getByRole('button', { name: 'Download anyway ⬇' }).click();
      await saved(download, filed);
    });
    await step('the blanks are answered and the officer signs: "The signed PDF is still downloadable above."', async () => {
      await page.reload();
      await page.getByLabel('12. Reason for Current Bid Request').selectOption('Renewal Increase');
      await page.getByLabel(/^16\. Within the past 12 months/).selectOption('No');
      const print = page.getByLabel('Print Name of Authorized Company Officer');
      await print.fill(officer);
      await print.press('Tab');
      await page.getByText('100% complete').waitFor();
      await page.getByLabel('Signer’s full name').fill(officer);
      await page.getByLabel(/written authorization to sign for them/).check();
      await page.getByRole('button', { name: 'Sign for the company officer' }).click();
      await page.getByRole('dialog').getByRole('button', { name: 'Sign', exact: true }).click();
      await page.getByText('The signed PDF is still downloadable above.').waitFor();
    });
    await step('the signed "Download PDF" passes every check and downloads the filed copy', async () => {
      await pick(page, 'Download PDF');
      const dialog = page.getByRole('dialog', { name: 'Before you download' });
      await dialog.getByText('✓ Nothing to fix: the file is ready to go.').waitFor();
      const download = page.waitForEvent('download', { timeout: 60000 });
      await dialog.getByRole('button', { name: 'Download ⬇' }).click();
      await saved(download, filed);
    });
    await step('Documents holds "Florida Blue 51+ — signed copy", and its Remove is refused', async () => {
      await page.getByRole('link', { name: 'Documents', exact: true }).click();
      await page.getByText('Florida Blue 51+ — signed copy').first().click();
      const remove = page.getByRole('button', { name: 'Remove', exact: true });
      await remove.waitFor();
      if (await remove.isEnabled()) throw new Error('Remove is offered on the signed copy');
      const why = await remove.getAttribute('title');
      if (!/signed form is kept/.test(why || '')) throw new Error(`Remove says ${why}`);
    });
  },
};
