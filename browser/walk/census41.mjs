// Slice 41's "done when" (plan.md §13 row 41; C1–C10, C25, C38): "Flagged errors are fixed with Excel keys; the blank
// template re-imports cleanly". Run it with `--need s41`.
//
// On GD4's Census tab: the roster draws with its frozen Person column; in ✎ Edit an arrow reaches a blank required
// medical tier, EE and Enter fill it and the blank count drops, Ctrl+Z puts it back; a date of birth typed wrong is
// underlined red and named in the error banner, and typing it right clears both; ＋ Dep ▸ Spouse lands in the new
// person's First Name and × removes them; the COBRA tick says who ticked it. Then ⬇ Blank template downloads the
// roster prefilled, and the same file comes back through the import door with every column Mapped and nobody changed.
// Everything it changes it puts back, but the template's import stays applied: `seed_golden GD4` resets the deal.

import os from 'node:os';
import path from 'node:path';

import { answerKey } from '../shared/golden.mjs';

async function api(page, base, url) {
  const response = await page.request.get(`${base}/api/${url}`);
  if (!response.ok()) throw new Error(`GET ${url} answered ${response.status()}`);
  return response.json();
}

const blanks = (summary) => summary.missing_required;

export const census41 = {
  title: 'Slice 41: on GD4’s roster flagged errors are fixed with Excel keys; the blank template re-imports cleanly',
  deal: 'GD4',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base } = ctx;
    const key = answerKey('GD4').census;
    const grid = page.getByRole('grid', { name: 'Census roster' });
    const rows = grid.getByRole('row');
    const subtitle = page.getByText(/ employees · \d+ dependents · /);
    let dealId;
    let labels = {};
    let heads = [];
    const cellIn = (row, field) => row.getByRole('gridcell').nth(heads.indexOf(labels[field]) - 1); // Person is a rowheader
    const census = () => api(page, base, `deals/${dealId}/census/`);
    const blankCount = async () => blanks((await census()).summary);
    const saysBlank = (n) => subtitle.filter({ hasText: n ? `· ${n} required cells blank ·` : '· Census OK ·' }).waitFor();

    await signIn(ctx);
    await openDeal(ctx);
    await step('the Census tab draws the roster: Person, the columns, the line chips and the key’s counts', async () => {
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      const meta = await api(page, base, 'meta/');
      labels = Object.fromEntries(meta.census.fields.map((field) => [field.key, field.label]));
      await page.getByRole('link', { name: 'Census', exact: true }).click();
      await grid.getByRole('columnheader', { name: 'Person' }).waitFor({ timeout: 60000 });
      heads = (await grid.getByRole('columnheader').allInnerTexts()).map((text) => text.replace('ⓘ', '').trim());
      for (const field of ['first_name', 'dob', 'medical_tier', 'dental_tier', 'vision_tier']) {
        if (!heads.includes(labels[field])) throw new Error(`no ${labels[field]} column`);
      }
      for (const line of ['Medical', 'Dental', 'Vision']) await page.getByRole('button', { name: line, pressed: true }).waitFor();
      await subtitle.filter({ hasText: `${key.employees} employees · ${key.dependents} dependents ·` }).waitFor();
      const blank = Object.values(key.tiers).reduce((sum, tiers) => sum + tiers.blank, 0);
      await saysBlank(blank);
      if ((await rows.count()) !== key.employees + key.dependents + 1) throw new Error(`${await rows.count()} rows`);
    });
    await step('the Person column stays put while the roster scrolls right', async () => {
      const person = grid.getByRole('columnheader', { name: 'Person' });
      const first = grid.getByRole('columnheader', { name: labels.first_name });
      const before = [await person.boundingBox(), await first.boundingBox()];
      await grid.hover();
      await page.mouse.wheel(500, 0);
      await page.waitForTimeout(400);
      const after = [await person.boundingBox(), await first.boundingBox()];
      if (Math.abs(after[0].x - before[0].x) > 1) throw new Error(`Person moved ${before[0].x} → ${after[0].x}`);
      if (after[1].x >= before[1].x - 100) throw new Error('the roster did not scroll');
      await page.mouse.wheel(-500, 0);
    });
    await step('✎ Edit turns the roster into a spreadsheet: a blank required cell reads ＋ Add', async () => {
      await page.getByRole('button', { name: '✎ Edit' }).click();
      await page.getByRole('button', { name: 'Done ✓' }).waitFor();
      await grid.getByRole('gridcell', { name: '＋ Add' }).first().waitFor();
    });
    let blankRow;
    let before = 0;
    await step('an arrow reaches a blank medical tier; EE and Enter fill it and the blank count drops', async () => {
      before = await blankCount();
      blankRow = rows.filter({ has: page.getByRole('gridcell', { name: '＋ Add' }) }).first();
      const tier = cellIn(blankRow, 'medical_tier');
      if ((await tier.innerText()).trim() !== '＋ Add') throw new Error('the first blank row has its medical tier');
      await cellIn(blankRow, 'medical_plan').click();
      await page.keyboard.press('ArrowRight');
      await page.keyboard.type('EE');
      await page.keyboard.press('Enter');
      await tier.filter({ hasText: /^EE$/ }).waitFor();
      for (let tries = 0; (await blankCount()) >= before; tries += 1) {
        if (tries > 20) throw new Error(`still ${before} required cells blank`);
        await page.waitForTimeout(250);
      }
      await saysBlank(await blankCount());
    });
    await step('Ctrl+Z puts the tier back: ＋ Add again, and the count with it', async () => {
      await page.keyboard.press('Control+z');
      await cellIn(blankRow, 'medical_tier').filter({ hasText: '＋ Add' }).waitFor();
      for (let tries = 0; (await blankCount()) !== before; tries += 1) {
        if (tries > 20) throw new Error(`${await blankCount()} blank, not ${before}`);
        await page.waitForTimeout(250);
      }
      await saysBlank(before);
    });
    const first = rows.nth(1);
    let born = '';
    await step('a date of birth typed wrong is underlined red and named in the error banner', async () => {
      const dob = cellIn(first, 'dob');
      born = (await dob.innerText()).trim();
      await dob.click();
      await page.keyboard.type('13/45/1958');
      await page.keyboard.press('Enter');
      await page.getByText(/^1 validation error$/).waitFor();
      await page.getByText('in the census — hover a red cell to see why.', { exact: false }).waitFor();
      await grid.getByTitle('Could not read "13/45/1958" as a date').waitFor();
    });
    await step('Arrow up and typing the date right clears the underline and the banner', async () => {
      await page.keyboard.press('ArrowUp');
      await page.keyboard.type(born);
      await page.keyboard.press('Enter');
      await cellIn(first, 'dob').filter({ hasText: born }).waitFor();
      await page.getByText(/^\d+ validation errors?$/).waitFor({ state: 'detached' });
      await grid.getByTitle(/Could not read/).waitFor({ state: 'detached' });
    });
    const spouse = rows.nth(2);
    await step('＋ Dep ▸ Spouse adds a spouse under the first employee, the cursor waiting in First Name', async () => {
      // Home takes the cursor to the row's first cell, and the roster back to its left edge: the list closes on any
      // scroll (as the old one did), and a click's scroll-into-view of the frozen column would be one.
      await page.keyboard.press('Home');
      await page.waitForTimeout(300);
      await first.getByRole('button', { name: '＋ Dep' }).click();
      await page.getByRole('menuitem', { name: 'Spouse' }).waitFor();
      await page.waitForFunction(() => document.activeElement?.textContent === 'Spouse'); // the menu's first item
      await page.keyboard.press('Enter');
      await spouse.getByRole('rowheader', { name: /↳ Spouse/ }).waitFor();
      await page.waitForTimeout(300);
      await page.keyboard.type('Walkspouse');
      await page.keyboard.press('Enter');
      await cellIn(spouse, 'first_name').filter({ hasText: /^Walkspouse$/ }).waitFor();
      let added;
      for (let tries = 0; !added; tries += 1) {
        if (tries > 20) throw new Error('Walkspouse was not stored');
        await page.waitForTimeout(250);
        added = (await census()).members.find((m) => m.values.first_name === 'Walkspouse');
      }
      if (added.kind !== 'dependent' || added.values.relationship !== 'Spouse') throw new Error(`stored as ${added.kind}`);
    });
    await step('× removes the spouse again', async () => {
      await spouse.hover();
      await spouse.getByRole('button', { name: 'Remove this dependent' }).click();
      await page.getByText('Dependent removed').first().waitFor();
      await grid.getByRole('gridcell', { name: 'Walkspouse' }).waitFor({ state: 'detached' });
      if ((await rows.count()) !== key.employees + key.dependents + 1) throw new Error(`${await rows.count()} rows`);
    });
    await step('Done ✓ locks the roster again', async () => {
      await page.getByRole('button', { name: 'Done ✓' }).click();
      await page.getByRole('button', { name: '✎ Edit' }).waitFor();
    });
    await step('the COBRA tick says who ticked it and when; unticking puts it back', async () => {
      const tick = page.getByRole('checkbox', { name: /Check the COBRA administrator/ });
      await tick.click(); // it shows ticked once the server has the tick (the old CobraCheck's way)
      await page.getByText('COBRA participants are on this census.').waitFor();
      const { cobra } = await census();
      if (!cobra.checked || !cobra.by_name || !cobra.at) throw new Error(JSON.stringify(cobra));
      await page.getByText(`${cobra.by_name} · `, { exact: false }).first().waitFor();
      await page.getByRole('checkbox', { name: 'COBRA participants are on this census.' }).click();
      await tick.waitFor();
    });
    let file = '';
    await step('⬇ Blank template downloads the roster, prefilled', async () => {
      const download = page.waitForEvent('download');
      await page.getByRole('button', { name: '⬇ Blank template' }).click();
      const got = await download;
      file = path.join(os.tmpdir(), `walk-s41-${Date.now()}-${got.suggestedFilename()}`);
      await got.saveAs(file);
      await page.getByText('Census template downloaded').first().waitFor();
    });
    await step('the same file comes back through the import door with every column Mapped', async () => {
      const chooser = page.waitForEvent('filechooser');
      await page.getByRole('button', { name: 'Import another census file ▸' }).click();
      await (await chooser).setFiles(file);
      await page.getByText('Map census columns').waitFor({ timeout: 30000 });
      const words = await page.getByText(/ of \d+ columns mapped$/).innerText();
      const [, mapped, all] = words.match(/(\d+) of (\d+) columns mapped$/);
      if (mapped !== all) throw new Error(words);
      if ((await page.getByText('Mapped', { exact: true }).count()) !== Number(all)) throw new Error('a column is not Mapped');
      if (await page.getByText(/^(Unmapped|Check \(\d+%\))$/).count()) throw new Error('a column is unmapped or a guess');
    });
    await step('its dry run changes nobody, and applying it leaves the roster as it was', async () => {
      await page.getByRole('button', { name: 'Apply mapping & build roster ▸' }).click();
      const people = key.employees + key.dependents;
      await page.getByText(`0 added · 0 changed · 0 removed · 0 kept · ${people} unchanged`).waitFor();
      await page.getByRole('button', { name: 'Apply to the roster ▸' }).click();
      await page.getByText('Mapping applied — census normalized').first().waitFor();
      await subtitle.filter({ hasText: `${key.employees} employees · ${key.dependents} dependents ·` }).waitFor();
      if ((await blankCount()) !== before) throw new Error(`${await blankCount()} blank after the import`);
    });
  },
};
