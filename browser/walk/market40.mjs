// Slice 40's "done when" (plan.md §13.9 row 40; B13, B25–B35): GD6 reaches "Ready to market"; Mark as marketed records
// the skipped items and can be undone. Run it with `--need s40` on a freshly seeded GD6 (`seed_golden GD6`); it leaves
// GD6 marked as marketed, so seed it again afterwards.
//
// Everything a person does is done on the Intake tab: Market anyway ▸ (and its Undo, then the Activity row), a contact
// typed into Contacts, the BOR signed, Medical answered in force and the coverage confirmed, the checklist ticked, Mark
// as marketed. The census is the one thing landed through the API (a 60-person CSV, uploaded, imported and applied as
// the import door's Apply does): the Census tab's import is slice 12's walk, not this one.

import { answerKey } from '../shared/golden.mjs';

async function api(page, base, method, url, options = {}) {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
  const response = await page.request.fetch(`${base}/api/${url}`, {
    method,
    ...options,
    headers: { 'X-CSRFToken': csrf, Referer: base },
  });
  if (!response.ok()) throw new Error(`${method} ${url} answered ${response.status()}: ${await response.text()}`);
  return response.status() === 204 ? null : response.json();
}

/** GD6's 60 enrolled employees as a census file: the current plan's 30 EE, 10 ES, 8 EC and 12 FAM (synthetic). */
function censusCsv(plan) {
  const head = ['Employee ID', 'Relationship', 'First Name', 'Last Name', 'Date of Birth', 'Gender', 'Zip Code',
    'Hours Per Week', 'Medical Plan', 'Medical Tier'];
  const tiers = [...Array(30).fill('EE'), ...Array(10).fill('ES'), ...Array(8).fill('EC'), ...Array(12).fill('FAM')];
  const rows = tiers.map((tier, i) => {
    const n = i + 1;
    return [`W6-${String(n).padStart(3, '0')}`, 'Employee', `Walker${n}`, `Synthetic${n}`,
      `19${70 + (n % 25)}-0${1 + (n % 9)}-1${n % 9}`, n % 2 ? 'F' : 'M', '33602', '40', plan, tier];
  });
  return [head, ...rows].map((row) => row.join(',')).join('\n');
}

export const market40 = {
  title: 'Slice 40: GD6 reaches Ready to market; Mark as marketed records the skipped items and can be undone',
  deal: 'GD6',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec, base } = ctx;
    const key = answerKey('GD6').ready;
    const contact = spec.get_to_market.contacts[0];
    let dealId;
    const head = () => page.locator('.bnf-intake-head');
    const row = (label) => page.getByRole('group', { name: label, exact: true });
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Intake tab reads "Blocked — required items open" with Market anyway ▸, and the checklist its tier', async () => {
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      await page.getByRole('link', { name: 'Intake', exact: true }).click();
      await head().getByText('Blocked — required items open').waitFor();
      await head().getByRole('button', { name: 'Market anyway ▸' }).waitFor();
      await page.getByText(`${key.tier_label} · ${key.enrolled} enrolled — what carriers need before we market.`).waitFor();
      await page.getByText(`0/${key.at_ready.required} ready`).waitFor();
    });
    await step('Market anyway ▸ asks first, naming what is still open', async () => {
      await head().getByRole('button', { name: 'Market anyway ▸' }).click();
      const dialog = page.getByRole('dialog', { name: 'Send to market anyway?' });
      await dialog.getByText(/8 items still open: HR contact · Signed BOR · Census · Confirm current coverage/).waitFor();
      await dialog.getByRole('button', { name: 'Market anyway' }).click();
    });
    await step('the badge reads Sent to market, the checklist "Sent to market <date>", the toast offers Undo', async () => {
      await head().getByText('Sent to market', { exact: true }).waitFor();
      await page.getByText(/^Sent to market \d\d\/\d\d\/\d{4}$/).waitFor();
      if (await head().getByRole('button', { name: /Market anyway|Mark as marketed/ }).count()) throw new Error('a market button is still offered');
      await page.getByText(/^Marked as sent to market anyway · Undo$/).waitFor();
    });
    await step('Undo takes it back: Blocked again', async () => {
      await page.getByRole('button', { name: 'Undo', exact: true }).click();
      await page.getByText('Undone — not sent to market').waitFor();
      await head().getByText('Blocked — required items open').waitFor();
    });
    await step('the Activity drawer records the skipped items, and the Undo', async () => {
      await page.getByRole('button', { name: 'Activity', exact: true }).click();
      await page.getByText(/^Marked as marketed anyway, skipping 8: HR contact, Signed BOR, Census, Confirm current coverage/).first().waitFor();
      await page.getByText(/^Reverted: Marked as marketed anyway, skipping 8/).first().waitFor();
      await page.keyboard.press('Escape');
    });
    await step('＋ Add contact, then the HR admin’s name and email typed in: Contacts OK', async () => {
      await page.getByRole('button', { name: '＋ Add contact' }).click();
      const card = page.getByRole('group', { name: /^Contact / }).first();
      await card.getByLabel('Name').waitFor();
      await card.getByLabel('Name').fill(contact.name);
      await card.getByLabel('Email').click(); // the name saves on blur
      await card.getByLabel('Email').fill(contact.email);
      await card.getByLabel('Phone').click();
      await page.getByRole('group', { name: `Contact ${contact.name}` }).waitFor();
      await page.waitForFunction(async ([url]) => (await (await fetch(url)).json()).contacts_ok === true,
        [`${base}/api/deals/${dealId}/intake/`], { timeout: 10000 });
    });
    await step('the BOR signed with a typed name: "Signed by …"', async () => {
      await page.getByLabel('Signer full name (BOR)').fill(spec.get_to_market.bor_signer);
      await page.getByRole('button', { name: 'Sign BOR' }).click();
      await page.getByText(`Signed by ${spec.get_to_market.bor_signer}`).waitFor();
    });
    await step('the 60-person census lands (API: upload, import, Apply) and the census row is done', async () => {
      const plan = spec.plans.find((p) => p.role === 'current').name;
      const document = await api(page, base, 'POST', `deals/${dealId}/documents/`, {
        multipart: {
          file: { name: 'Walk 40 census (synthetic).csv', mimeType: 'text/csv', buffer: Buffer.from(censusCsv(plan)) },
          kind: 'census',
          lines: '[]',
        },
      });
      const proposed = await api(page, base, 'POST', `deals/${dealId}/census/imports/`, { data: { document_id: document.id } });
      await api(page, base, 'POST', `census/imports/${proposed.id}/apply/`);
      await page.reload();
      await row('Member-level census').getByText('✓').waitFor();
    });
    await step('Medical answered in force, then Confirm coverage & intent: ✓ Confirmed', async () => {
      await page.getByRole('checkbox', { name: 'Medical in force' }).click();
      await page.getByRole('checkbox', { name: 'Medical in force', checked: true }).waitFor();
      await page.getByRole('button', { name: 'Confirm coverage & intent' }).click();
      await page.getByText('✓ Confirmed', { exact: true }).waitFor();
      await row('Confirm current coverage & what we’re shopping').getByText('✓').waitFor();
    });
    await step('COBRA Confirmed; the questionnaire, renewal and invoice On file: 6/6 ready', async () => {
      const ticks = [['COBRA participants', 'Confirmed'], ['Medical questionnaire — completed & signed', 'On file'],
        ['Current benefits renewal & rates', 'On file'], ['Current invoice(s)', 'On file']];
      for (const [label, word] of ticks) {
        await row(label).getByLabel(word).click(); // the tick shows once the server has it, as the old card's did
        await row(label).getByText('✓', { exact: true }).waitFor();
        await row(label).getByLabel(word, { checked: true }).waitFor();
      }
      await page.getByText(`${key.at_ready.done}/${key.at_ready.required} ready`).waitFor();
    });
    await step('the badge reads "Ready to market"; Mark as marketed sends it, with nothing skipped', async () => {
      await head().getByText('Ready to market', { exact: true }).waitFor();
      await head().getByRole('button', { name: 'Mark as marketed' }).click();
      await page.getByText(/^Marked as sent to market · Undo$/).waitFor();
      await head().getByText('Sent to market', { exact: true }).waitFor();
      const body = await api(page, base, 'GET', `deals/${dealId}/intake/`);
      if (body.ready.state !== 'submitted' || body.ready.gaps.length) throw new Error(`state ${body.ready.state}`);
      const header = await api(page, base, 'GET', `deals/${dealId}/`);
      if (header.stage !== 'intake') throw new Error(`the stage moved to ${header.stage} (OQ52: it moves no stage)`);
    });
  },
};
