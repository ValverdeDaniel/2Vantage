// Slice 45's "done when" (plan.md §13.9 row 45; K34–K42, K79–K98): on GD4 (the 160-person census) the RFP packet's
// census rows download the Warner, Aetna, Angle (and its portal CSV) and UHC files, each the carrier's own workbook
// filled in place, and the Census tab's lens checks each format. The files are saved to $WALK_FILES (default: the
// system temp folder) so the parity tools image can open and render them with LibreOffice (tools/parity/README.md).
// It ticks and unticks Angle's CSV, so GD4's request ends where it began (no carrier is picked: GD4's census
// requirements are not moved); it writes only the request's own row and the downloads' "downloaded" rows.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CARRIERS = ['Warner Pacific', 'Aetna', 'Angle Health', 'UnitedHealthcare'];

async function saved(page, row, wanted) {
  const download = page.waitForEvent('download', { timeout: 60000 });
  await row.getByRole('button', { name: 'Download ⬇' }).click();
  const got = await download;
  if (got.suggestedFilename() !== wanted) throw new Error(`the file is named ${got.suggestedFilename()}`);
  const folder = process.env.WALK_FILES || path.join(os.tmpdir(), 'walk-s45');
  fs.mkdirSync(folder, { recursive: true });
  const file = path.join(folder, wanted);
  await got.saveAs(file);
  const head = fs.readFileSync(file).subarray(0, 4).toString('latin1');
  if (wanted.endsWith('.xlsx') && head !== 'PK\u0003\u0004') throw new Error('not a workbook');
  if (wanted.endsWith('.csv') && !fs.readFileSync(file, 'utf8').includes('First Name*')) throw new Error('not Angle');
}

// Reload and wait for `ready`, riding out a dev-server restart (other lanes' edits reload Django for ~30 s).
async function reloaded(page, ready) {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    await page.reload();
    try {
      await ready().waitFor({ timeout: 20000 });
      return;
    } catch (error) {
      if (attempt === 5) throw error;
      await page.waitForTimeout(5000);
    }
  }
}

export const rfp45 = {
  title: "Slice 45: GD4's RFP packet downloads each carrier's own census file; the Census tab's lens checks it",
  deal: 'GD4',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const safe = spec.client.replace(/[^A-Za-z0-9 ._-]/g, '').trim();
    const packet = () => page.locator('[data-guide="rfp-packet"]');
    const row = (key) => page.locator(`[data-guide="rfp-row-${key}"]`);
    await signIn(ctx);
    await openDeal(ctx);
    await step('the RFP packet lists the four carrier census formats and Angle’s portal CSV, off on purpose', async () => {
      await page.getByRole('link', { name: 'RFP', exact: true }).click();
      await page.waitForURL(/\/deals\/\d+\/rfp$/);
      await packet().getByText('Carrier census formats').waitFor({ timeout: 45000 });
      // A walk cut short earlier can leave the CSV ticked: start from the recommendation.
      if (await row('census-angle-csv').getByRole('checkbox').isChecked()) {
        await row('census-angle-csv').getByRole('checkbox').click();
        await row('census-angle-csv').getByText(/^Off on purpose — /).waitFor();
      }
      for (const carrier of CARRIERS) await packet().getByText(`${carrier} census`, { exact: true }).waitFor();
      await row('census-angle-csv').getByText('↳ CSV for their portal').waitFor();
      await row('census-angle-csv').getByText(/^Off on purpose — The same census/).waitFor();
      await row('census-warner').getByText('Any carrier').waitFor();
      await packet().getByText('4 of 5 in packet · 1 off on purpose').first().waitFor();
    });
    await step('ticking Angle’s CSV by hand says so and is kept; unticking puts it back', async () => {
      // A click, then the row's own words: the box is controlled, so it turns once the page redraws.
      await row('census-angle-csv').getByRole('checkbox').click();
      await row('census-angle-csv').getByText(/^Ticked by hand — /).waitFor();
      await row('census-angle-csv').getByText('your pick').waitFor();
      await reloaded(page, () => packet().getByText('5 of 5 in packet').first());
      await row('census-angle-csv').getByRole('checkbox').click();
      await packet().getByText('4 of 5 in packet · 1 off on purpose').first().waitFor();
    });
    for (const [key, carrier, kind] of [
      ['census-warner', 'Warner Pacific', 'xlsx'],
      ['census-aetna', 'Aetna', 'xlsx'],
      ['census-angle', 'Angle Health', 'xlsx'],
      ['census-angle-csv', 'Angle Health', 'csv'],
      ['census-uhc', 'UnitedHealthcare', 'xlsx'],
    ]) {
      const name = `${safe} - ${carrier} census.${kind}`;
      await step(`Download ⬇ on ${key} saves "${name}"`, async () => saved(page, row(key), name));
    }
    await step('Check ▸ on UnitedHealthcare opens its lens on the Census tab: readiness, chips, columns, rows', async () => {
      await row('census-uhc').getByRole('link', { name: 'Check ▸' }).click();
      await page.waitForURL(/\/deals\/\d+\/census\?lens=census-uhc$/);
      await page.getByText('Export readiness').waitFor({ timeout: 45000 });
      await page.locator('[data-guide="census-lens-chips"]').getByText('Our census').waitFor();
      await page.locator('.bnf-lens-head').getByText('UnitedHealthcare census').waitFor();
      await page.getByText('rows 4–353, columns A–X of A–BX printed', { exact: false }).waitFor();
      await page.getByRole('cell', { name: '*Out of Area (Medical Only)' }).waitFor();
      await page.getByText('Exactly what UnitedHealthcare receives').waitFor();
      await page.getByText(/Printed on their sheet, never sent — 52 columns/).waitFor();
    });
    await step('Check the real file ▸ builds it and shows the roster sheet as Excel draws it', async () => {
      await page.getByRole('button', { name: 'Check the real file ▸' }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByRole('tab', { name: 'Employee Info' }).and(page.locator('[aria-selected="true"]')).waitFor({
        timeout: 45000,
      });
      await dialog.getByText(/^Rows 1–\d+ of 163$/).waitFor();
      await dialog.getByRole('tab', { name: 'Group Info' }).click();
      await dialog.getByText('*Total Employees Applying').waitFor();
      await page.keyboard.press('Escape');
    });
    await step('the Angle chip shows its two formats; "Our census" brings the roster back', async () => {
      await page.locator('[data-guide-lens="census-angle"]').getByText('XLSX | CSV').waitFor();
      await page.locator('[data-guide-lens="census-angle"]').click();
      await page.locator('.bnf-lens-head').getByText('Angle Health census').waitFor();
      await page.getByRole('button', { name: /Our census/ }).click();
      await page.getByRole('grid', { name: 'Census roster' }).waitFor();
    });
  },
};
