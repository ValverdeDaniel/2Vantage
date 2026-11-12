// Slice 46's "done when" (plan.md §13.9 row 46; K43–K68, K99–K104, K120; Q.9 row 46 on GD6): on GD6 (60 enrolled,
// so the request goes direct) the RFP packet shows the cover, Warner's form off on purpose and the Florida Blue
// questionnaire; the Emails card drafts one email per picked carrier; "Open in Outlook ⬇" checks, then saves an .eml
// that is an unsent draft (X-Unsent: 1, no From) with the cover and the questionnaire attached — there is no Outlook
// on the walk machine, so the file is read back as Outlook reads it; the first Sent tick moves the deal to Quoting;
// and the Proposal builder's Markets checked lists who was asked. Run on a freshly seeded GD6
// (`manage.py seed_golden GD6`); it leaves GD6 picked and sent, so re-seed it after. Files go to $WALK_FILES.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const folder = () => process.env.WALK_FILES || path.join(os.tmpdir(), 'walk-s46');

// Click a download door, read the check, download (anyway), and save the file; returns its path and text.
async function checked(page, button) {
  await button.click();
  const dialog = page.getByRole('dialog', { name: 'Before you download' });
  const go = dialog.getByRole('button', { name: /^Download( anyway)? ⬇$/ });
  await go.waitFor({ timeout: 60000 });
  const download = page.waitForEvent('download', { timeout: 90000 });
  await go.click();
  const got = await download;
  fs.mkdirSync(folder(), { recursive: true });
  const file = path.join(folder(), got.suggestedFilename());
  await got.saveAs(file);
  // Folded header lines (RFC 5322 §2.2.3) read as one, the way a mail reader unfolds them.
  const text = fs.readFileSync(file).toString('latin1').replace(/\r?\n[ \t]+/g, ' ');
  return { file, name: got.suggestedFilename(), text };
}

export const rfp46 = {
  title: 'Slice 46: GD6 direct — the packet, an .eml that opens as an unsent draft, the first Sent tick to Quoting',
  deal: 'GD6',
  async run(ctx, { signIn, openDeal }) {
    const { page, step } = ctx;
    const packet = () => page.locator('[data-guide="rfp-packet"]');
    const drafts = () => page.locator('[data-guide="carriers-drafts"]');
    const row = (key) => page.locator(`[data-guide="rfp-row-${key}"]`);
    const draft = (key) => page.locator(`[data-guide="rfp-draft-${key}"]`);
    await signIn(ctx);
    await openDeal(ctx);
    await step('the RFP tab goes direct (60 enrolled) and the Emails card waits for carriers', async () => {
      await page.getByRole('link', { name: 'RFP', exact: true }).click();
      await page.waitForURL(/\/deals\/\d+\/rfp$/);
      await drafts().getByText('Pick the carriers above — each one gets its own draft.').waitFor({ timeout: 45000 });
      await row('cover').getByText('RFP cover page').waitFor();
      await row('form').getByText(/^Off on purpose — Warner’s form goes only to Warner/).waitFor();
      await row('questionnaire-fl_blue_51').getByText('💡 Not signed by the employer yet').waitFor();
      await packet().getByText('Not set up').waitFor();
    });
    await step('picking Florida Blue and UnitedHealthcare makes one draft each, the questionnaire for Florida Blue', async () => {
      for (const name of ['Florida Blue', 'UnitedHealthcare']) {
        await page.locator('[data-guide="carriers-medical"]').getByRole('button', { name: new RegExp(`^${name}`) }).click();
      }
      await draft('florida_blue').waitFor({ timeout: 30000 });
      await draft('unitedhealthcare').waitFor();
      await draft('florida_blue').getByText(/Medical questionnaire — Florida Blue/).waitFor();
      if (await draft('unitedhealthcare').getByText(/Medical questionnaire/).count()) {
        throw new Error('the questionnaire rides to UnitedHealthcare');
      }
      await drafts().getByText('Marked sent 0 of 2').waitFor();
    });
    await step('Open in Outlook ⬇ checks first, then saves an unsent draft with its files (X-Unsent: 1, no From)', async () => {
      const got = await checked(page, draft('florida_blue').getByRole('button', { name: 'Open in Outlook ⬇' }));
      if (!got.name.endsWith(' - RFP email - Florida Blue.eml')) throw new Error(`the draft is named ${got.name}`);
      const head = got.text.split(/\r?\n\r?\n/)[0].split('\n').map((line) => line.trim());
      if (!head.includes('X-Unsent: 1')) throw new Error('no X-Unsent: 1 header');
      if (head.some((line) => line.startsWith('From:'))) throw new Error('the draft carries a From header');
      if (!head.some((line) => /^Subject: RFP: .+ \| eff\. 04\/01\/2027 \| Med$/.test(line))) {
        throw new Error('unexpected subject');
      }
      for (const wanted of ['RFP cover page.pdf', 'medical-questionnaire.pdf']) {
        if (!got.text.includes(wanted)) throw new Error(`${wanted} is not attached`);
      }
    });
    await step('the first Sent tick moves the deal to Quoting and counts the send', async () => {
      await draft('florida_blue').getByRole('checkbox').click();
      await drafts().getByText('Marked sent 1 of 2').waitFor({ timeout: 30000 });
      await page.locator('[title="Deal stage"]').getByText('Quoting', { exact: true }).waitFor({ timeout: 30000 });
      await page.locator('[data-guide="rfp-mark-marketed"]').waitFor();
    });
    await step("the Proposal builder's Markets checked lists Florida Blue as asked", async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'Proposal builder' }).click();
      // GD6 quotes medical alone, so the builder opens on it with no line tabs.
      await page.getByRole('textbox', { name: 'Note for Florida Blue' }).waitFor({ timeout: 45000 });
      if (await page.getByText('No RFP email is marked sent yet', { exact: false }).count()) {
        throw new Error('Markets checked still says no RFP was sent');
      }
      // Florida Blue was asked; UnitedHealthcare quoted but its email is not marked sent.
      const uhc = page.getByRole('row').filter({ has: page.getByRole('textbox', { name: 'Note for UnitedHealthcare' }) });
      await uhc.getByText('not on the RFP').waitFor();
      const blue = page.getByRole('row').filter({ has: page.getByRole('textbox', { name: 'Note for Florida Blue' }) });
      if (await blue.getByText('not on the RFP').count()) throw new Error('Florida Blue is not listed as asked');
    });
  },
};
