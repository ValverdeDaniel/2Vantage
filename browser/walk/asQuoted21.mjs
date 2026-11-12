// Need 3, recreate a scanned quote's order and rows (plan.md §13.7 row 21, "done when"; V.2 need 3; D66, E42, F42;
// Q.9 row 21; OQ32's default: both screens): on GD3 the renewal packet's read is used, then the Advisor's "As quoted"
// shows the packet in the file's column order (each current plan, then its renewal) with its printed rows, the row
// that fills no field ("Chiropractic visits") greyed with its printed text; Documents shows the same "As in the file"
// beside the file; ↶ Undo this run takes the plans and the table off again.
//
// Run it with `--need 3` on a freshly seeded GD3 (`manage.py seed_golden GD3`). When a read of the packet already
// waits for review it uses that one; otherwise it makes ONE REAL Claude read (Sonnet 5.5, about $0.05 of the build's
// $20 cap, `manage.py ai_spend`; the backend needs ANTHROPIC_API_KEY and the worker must be running). It leaves GD3 at
// checkpoint A again (Quoting: the stage only moves forward).

const READ_MS = 300000; // a real read of the packet takes about a minute
// The packet's printed rows, in printed order (the quote reader's corpus table that prints GD3's packet).
const PRINTED_ROWS = [
  'Plan type',
  'Network',
  'Metal level',
  'Deductible (single / family)',
  'Out-of-pocket max (single)',
  'Primary care copay',
  'Chiropractic visits',
  'Employee only',
  'Employee + spouse',
  'Employee + child(ren)',
  'Family',
];
const UNMAPPED = 'Chiropractic visits';
const PRINTED_TITLE = 'As the file prints it: this row fills no field, so it is never a value';

async function heads(table) {
  const texts = await table.locator('thead th').evaluateAll((ths) => ths.slice(1).map((th) => th.innerText));
  return texts.map((text) => text.replace(/\s+/g, ' ').trim());
}

async function labels(table) {
  return table.locator('tbody tr').evaluateAll((rows) =>
    rows.filter((row) => row.cells.length > 1).map((row) => row.cells[0].innerText.split('·')[0].trim()),
  );
}

async function checkTable(page, first, second, renewalRate) {
  const table = page.getByRole('table').filter({ hasText: 'As printed on page 2' }).first();
  await table.waitFor();
  const order = (await heads(table)).map((text) => `${/RENEWAL/.test(text) ? 'renewal' : /CURRENT/.test(text) ? 'current' : '?'} ${text.includes(first) ? 'D' : text.includes(second) ? 'F' : '?'}`);
  if (order.join() !== 'current D,renewal D,current F,renewal F') throw new Error(`columns: ${order.join(' | ')}`);
  const rows = [...new Set(await labels(table))];
  if (rows.join('|') !== PRINTED_ROWS.join('|')) throw new Error(`rows: ${rows.join(' | ')}`);
  const greyed = table.getByTitle(PRINTED_TITLE);
  if ((await greyed.count()) !== 4) throw new Error(`greyed printed cells: ${await greyed.count()}`);
  const printed = await greyed.evaluateAll((cells) => cells.map((cell) => cell.innerText.trim()));
  if (printed.some((text) => text !== '20 a year')) throw new Error(`printed text: ${printed.join(' | ')}`);
  const ee = table.locator('tbody tr').filter({ hasText: 'Employee only' });
  if (!(await ee.innerText()).includes(renewalRate)) throw new Error(`the live EE rate ${renewalRate} is not shown`);
}

export const asQuoted21 = {
  title: 'As quoted: GD3’s packet in the file’s column order with its printed rows, on the Advisor and beside the file (D66, E42, F42)',
  deal: 'GD3',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const [first, second] = spec.arrivals.map((plan) => plan.name);
    const renewalRate = Number(spec.renewal_packet.renewals[spec.arrivals[0].ref].rate_ee).toFixed(2);
    await signIn(ctx);
    await openDeal(ctx);

    await step('Documents opens on the packet, and its read waits for review (read now when none waits)', async () => {
      await page.getByRole('link', { name: 'Documents', exact: true }).click();
      await page.getByRole('tab', { name: /2027 Renewal/ }).first().click();
      const waiting = page.getByText('Review this scan');
      try {
        await waiting.waitFor({ timeout: 8000 });
      } catch {
        await page.getByRole('button', { name: '↻ Re-read…' }).click();
        await page.getByRole('button', { name: 'Re-read 1 file' }).click();
        await waiting.waitFor({ timeout: READ_MS });
      }
    });
    await step('"Use this scan ▸" lands the two current plans and their renewals', async () => {
      await page.getByRole('button', { name: 'Use this scan ▸' }).click();
      await page.getByText('✓ Used Claude’s read — 2 current plans · 2 renewals').waitFor({ timeout: 30000 });
    });
    await step('the Advisor offers "As quoted", which shows the packet as printed', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'As quoted' }).click();
      await page.getByText(/As printed on page 2 of “2027 Renewal/).waitFor();
    });
    await step(
      'its columns keep the file’s order and its rows the printed order; the row that fills no field is greyed, as printed',
      () => checkTable(page, first, second, renewalRate),
    );
    await step('Documents shows the same table "As in the file", beside the file', async () => {
      await page.getByRole('link', { name: 'Documents', exact: true }).click();
      await page.getByRole('tab', { name: /2027 Renewal/ }).first().click();
      await page.getByRole('button', { name: /As in the file/ }).click();
      await checkTable(page, first, second, renewalRate);
      await page.getByRole('button', { name: /List/ }).first().click(); // leave the kept view as it was
    });
    await step('↶ Undo this run takes the plans and the table off: "As quoted" is no longer offered', async () => {
      await page.getByRole('button', { name: '↶ Undo this run' }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByRole('button', { name: 'Undo this run', exact: true }).click();
      await page.getByText(/Undone — the deal is back to how it was before that read/).waitFor({ timeout: 30000 });
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'Quote comparison' }).waitFor();
      await page.getByRole('button', { name: 'As quoted' }).waitFor({ state: 'detached', timeout: 30000 });
    });
  },
};
