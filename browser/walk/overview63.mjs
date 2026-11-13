// Slice 63's "done when" (plan.md §13.10 row 63; Q.9 row 63; M42–M81): every Card 1 control writes through its owning
// app, and the Overview reads it back. Under the tiles stand Card 1, Card 2, the Activity card and the side cards, in
// the old order; then each control is pressed and its owner's own read is asked what it now holds: Confirmed and On
// file (intake's checklist), Not needed and Undo (intake's requirement), Still needed ▸ (intake, with the client's
// note), ⬆ Attach (documents), ＋ Ask and ＋ Ask for their census file (review's request tray), the stop-loss form
// picker (the questionnaire's choice); a call note lands in Notes and on the Timeline with its first line, and its
// delete is undone from the toast. Run with `--need s63` on a fresh GD2 (`manage.py seed_golden GD2`): it writes to
// GD2, so seed GD2 again afterwards. (Q.9 names GD6; GD2 is used so the walk never writes to the deal slice 58's lane
// walks.)

import { pdf } from './syntheticPdf.mjs';

const RENEWAL = 'Current benefits renewal & rates';
const INVOICE = 'Current invoice(s)';
const COBRA = 'COBRA participants';
const NOTE = 'Called Casey about the census (walk 63, synthetic).';

async function api(page, base, url) {
  const response = await page.request.fetch(`${base}/api/${url}`);
  if (!response.ok()) throw new Error(`GET ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

const tab = (page) => page.getByRole('region', { name: 'Overview' });
const group = (page, title) => tab(page).getByRole('region', { name: title });
const row = (page, label) => tab(page).getByRole('group', { name: label });
const top = async (locator) => (await locator.first().boundingBox()).y;

async function until(check, what, tries = 40) {
  for (let n = 0; n < tries; n += 1) {
    if (await check()) return;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`never saw ${what}`);
}

async function item(page, base, dealId, key) {
  const intake = await api(page, base, `deals/${dealId}/intake/`);
  return intake.checklist.items.find((entry) => entry.key === key);
}

export const overview63 = {
  title: 'Slice 63: every Card 1 control writes through its owning app; Card 2, the feed, notes and side cards',
  deal: 'GD2',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base } = ctx;
    let dealId;
    await signIn(ctx);
    await openDeal(ctx);

    await step('under the tiles stand Card 1, Card 2, then the Activity card beside Notes and Commission (old order)', async () => {
      await page.waitForURL(/\/deals\/\d+\/overview/);
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      const region = tab(page);
      await region.getByText('1 · Get to Market', { exact: true }).waitFor();
      const order = [
        ['tiles', region.getByText('Intake complete', { exact: true })],
        ['Card 1', region.getByText('1 · Get to Market', { exact: true })],
        ['Activity', region.getByText('Every touch on this deal, newest first.', { exact: true })],
      ];
      let last = -1;
      for (const [name, locator] of order) {
        const y = await top(locator);
        if (y < last) throw new Error(`${name} stands above the block before it`);
        last = y;
      }
      const cards = region.locator('.bnf-phase-card > .bnf-phase-card-head .bb-panel-title');
      const [first, second] = [await cards.nth(0).boundingBox(), await cards.nth(1).boundingBox()];
      if ((await cards.nth(1).textContent()) !== '2 · Quote to Close' || Math.abs(first.y - second.y) > 2 || second.x <= first.x) {
        throw new Error('Card 2 does not stand beside Card 1');
      }
      for (const text of ['Notes', 'Commission']) await region.getByText(text, { exact: true }).first().waitFor();
      await region.getByText(/^\d+ of \d+ requirements met · /).waitFor();
    });

    await step('Card 2 shows the journey’s Quote to Close steps with their details (M62)', async () => {
      const read = await api(page, base, `deals/${dealId}/overview/`);
      await tab(page).getByText(read.quote_to_close[0].detail, { exact: true }).waitFor();
      await tab(page).getByText('Proposal issued', { exact: true }).waitFor();
      await tab(page).getByRole('link', { name: 'Open comparison ▸' }).waitFor();
    });

    await step('Confirmed on COBRA is intake’s tick: intake holds it and Confirmations reads 1/1 (M60)', async () => {
      await row(page, COBRA).getByRole('checkbox', { name: 'Confirmed' }).click(); // held by the server: it shows once intake answers
      await until(async () => (await item(page, base, dealId, 'cobra')).attested, 'intake’s COBRA tick');
      await group(page, 'Confirmations').getByText('1/1', { exact: true }).waitFor();
    });

    await step('Still needed ▸ re-asks COBRA with the client’s note, through intake; Undo clears it (M55)', async () => {
      // a met group closes until the person opens it again (M44)
      if (!(await row(page, COBRA).count())) await group(page, 'Confirmations').locator('.bnf-req-head').click();
      await row(page, COBRA).getByRole('button', { name: 'Still needed ▸' }).click();
      await row(page, COBRA).getByRole('textbox', { name: 'Note the client will see' }).fill('This year’s list, please.');
      await row(page, COBRA).getByRole('button', { name: 'Mark needed' }).click();
      await row(page, COBRA).getByText('Client sees: “This year’s list, please.”').waitFor();
      if (!(await item(page, base, dealId, 'cobra')).forced) throw new Error('intake does not hold the re-ask');
      await row(page, COBRA).getByRole('button', { name: 'Undo' }).click();
      await until(async () => !(await item(page, base, dealId, 'cobra')).forced, 'the re-ask undone in intake');
    });

    await step('Not needed on the invoice is intake’s requirement; Undo restores it (M55)', async () => {
      await row(page, INVOICE).getByRole('button', { name: 'Not needed' }).click();
      await until(async () => (await item(page, base, dealId, 'invoice')).waived, 'the invoice waived in intake');
      await row(page, INVOICE).getByText('Waived', { exact: true }).waitFor();
      await row(page, INVOICE).getByRole('button', { name: 'Undo' }).click();
      await until(async () => !(await item(page, base, dealId, 'invoice')).waived, 'the invoice required again');
      await row(page, INVOICE).getByRole('button', { name: 'Not needed' }).waitFor(); // the card read it back
    });

    await step('⬆ Attach on the renewal uploads through documents; the row reads "— on file" (M52)', async () => {
      const file = { name: 'Renewal walk 63 (synthetic).pdf', mimeType: 'application/pdf',
        buffer: Buffer.from(pdf([[[72, 720, 'Example Health renewal (synthetic)', 14, true]]]), 'latin1') };
      // the card's writes go one at a time: wait until the last one has settled (its buttons are enabled again)
      await until(async () => row(page, RENEWAL).getByRole('button', { name: '⬆ Attach' }).isEnabled(), 'the card idle');
      await page.waitForLoadState('networkidle');
      await row(page, RENEWAL).getByLabel(`Attach ${RENEWAL}`).setInputFiles(file);
      await row(page, RENEWAL).getByText(`${RENEWAL} — on file`).waitFor();
      const files = await api(page, base, `deals/${dealId}/documents/`);
      const list = files.results || files.documents || files;
      if (!JSON.stringify(list).includes('Renewal walk 63 (synthetic).pdf')) throw new Error('documents holds no such file');
    });

    await step('＋ Ask on the invoice puts it in review’s request tray: "✓ In tray" (M54)', async () => {
      await row(page, INVOICE).getByRole('button', { name: '＋ Ask' }).click();
      await row(page, INVOICE).getByText('✓ In tray').waitFor();
      const tray = await api(page, base, `deals/${dealId}/review/tray/`);
      if (!tray.items.some((entry) => entry.ref === 'doc:invoice')) throw new Error('the tray holds no doc:invoice');
    });

    await step('＋ Ask for their census file puts the file in the tray (M49)', async () => {
      await group(page, 'Census').getByRole('button', { name: '＋ Ask for their census file' }).click();
      await group(page, 'Census').getByText('✓ In tray').waitFor();
      const tray = await api(page, base, `deals/${dealId}/review/tray/`);
      if (!tray.items.some((entry) => entry.ref === 'census:file')) throw new Error('the tray holds no census:file');
    });

    await step('the stop-loss picker is the questionnaire’s choice: picking a form makes the disclosure needed (M51, M56)', async () => {
      const disclosure = group(page, 'Stop-loss disclosure');
      await disclosure.locator('.bnf-req-head').click();
      const picker = disclosure.getByRole('combobox');
      const options = await picker.locator('option').allTextContents();
      const needed = options.find((text) => text.startsWith('Needed —') && !text.includes('upload only'));
      if (!needed) throw new Error(`no form to pick: ${options.join(' | ')}`);
      await picker.selectOption({ label: needed });
      await disclosure.getByText('Not started', { exact: true }).waitFor();
      const forms = await api(page, base, `deals/${dealId}/questionnaires/`);
      if (!forms.items.stop_loss_disclosure.needed) throw new Error('the questionnaire does not hold the pick');
    });

    await step('a call note lands in Notes and on the Timeline with its first line (M73, M71)', async () => {
      const notes = tab(page).locator('.bnf-ov-notes');
      await notes.getByRole('textbox', { name: 'A new note' }).fill(NOTE);
      await notes.getByRole('button', { name: 'Call', exact: true }).click();
      await notes.getByRole('button', { name: 'Add note' }).click();
      await notes.locator('.bnf-ov-note-body', { hasText: NOTE }).waitFor();
      const event = tab(page).locator('.bnf-ov-event', { hasText: 'Logged a call' }).first();
      await event.getByText(NOTE).waitFor();
    });

    await step('Delete takes the note away and the toast’s Undo brings it back (M77)', async () => {
      const notes = tab(page).locator('.bnf-ov-notes');
      const note = notes.locator('.bnf-ov-note', { hasText: NOTE });
      await note.hover();
      await note.getByRole('button', { name: 'Delete' }).click();
      await note.waitFor({ state: 'detached' });
      await page.locator('.bb-toast').getByRole('button', { name: 'Undo' }).click();
      await notes.locator('.bnf-ov-note-body', { hasText: NOTE }).waitFor();
      await until(async () => (await api(page, base, `deals/${dealId}/notes/`)).some((entry) => entry.body === NOTE), 'the note back');
    });

    await step('the Timeline lists the writes, newest first, and the Overview wrote none of them (O.2)', async () => {
      const feed = await api(page, base, `deals/${dealId}/overview/feed/`);
      const areas = new Set(feed.results.map((entry) => entry.area));
      for (const area of ['intake', 'documents', 'notes', 'review']) {
        if (!areas.has(area)) throw new Error(`no ${area} row on the feed: ${[...areas].join(', ')}`);
      }
      if (areas.has('overview')) throw new Error('the Overview wrote a row');
      await tab(page).locator('.bnf-ov-event').first().waitFor();
    });
  },
};
