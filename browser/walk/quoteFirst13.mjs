// Need 6, quote-first (plan.md §13.6 row 13, "done when"; F85, F88, F91; Q.9 row 13): on GD3 every medical plan prices
// from typed counts; a second current plan names the plans that lost their price and opens the split; a census import
// re-prices them with "Priced from the census now · Keep my typed counts"; counts typed after the import win again.
// Run it with `--need 6` on a freshly seeded GD3 (`manage.py seed_golden GD3`), which it leaves at checkpoint B.
//
// The renewal packet's two current plans arrive through the plans API, as the packet's read lands them from slice 18,
// and the census through the documents and census APIs (the Census tab's own walk is slice 41's); everything the
// person reads and clicks on the Advisor is the screen's. Every figure is checked against GD3's hand-worked key.

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
  return response.json();
}

const money = (n) => `$${n.toLocaleString('en-US')}`;

/** {plan name: Monthly total text} for every row the board draws, read from the screen. */
function totals(page) {
  return page.evaluate(() => {
    const table = [...document.querySelectorAll('table')].find((t) =>
      [...t.querySelectorAll('thead th')].some((th) => /Monthly total/i.test(th.innerText)),
    );
    const heads = [...table.tHead.rows[0].cells].map((cell) => cell.innerText.trim());
    const at = heads.findIndex((text) => /Monthly total/i.test(text));
    const plan = heads.findIndex((text) => /^Plan$/i.test(text));
    const out = {};
    for (const row of table.tBodies[0].rows) {
      const lines = (row.cells[plan]?.innerText ?? '').split('\n').map((line) => line.trim());
      const total = (row.cells[at]?.innerText ?? '').match(/^\s*(—|\$[\d,]+)/)?.[1] ?? '';
      for (const line of lines) out[line] = total; // the figure, without its ✎ counts mark
    }
    return out;
  });
}

/** A census of the spec's groups as a CSV: one row per employee, their plan and tier (no dependents needed). */
function censusCsv(census) {
  const rows = [['Employee ID', 'Relationship', 'First Name', 'Last Name', 'Date of Birth', 'Medical Plan', 'Medical Tier']];
  let n = 0;
  for (const group of census.groups) {
    for (let i = 0; i < group.n; i += 1) {
      n += 1;
      const id = `${census.id_prefix}-${String(n).padStart(3, '0')}`;
      rows.push([id, 'Employee', `Walker${n}`, 'Synthetic', `0${(n % 9) + 1}/15/198${n % 10}`, group.medical_plan, group.tier]);
    }
  }
  return rows.map((row) => row.join(',')).join('\n');
}

export const quoteFirst13 = {
  title: 'Quote-first: GD3 prices from typed counts; a second current plan opens the split; the census re-prices (F85–F91)',
  deal: 'GD3',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec, base } = ctx;
    const key = answerKey('GD3').checkpoints;
    const named = Object.fromEntries([...spec.plans, ...spec.arrivals].map((p) => [p.ref, p.name]));
    // The board refetches after each write: read it until it shows the key's figures, for up to 8 seconds.
    const priced = async (plans, refs) => {
      let wrong = refs;
      let shown = {};
      for (let tries = 0; wrong.length && tries < 32; tries += 1) {
        if (tries) await page.waitForTimeout(250);
        shown = await totals(page);
        wrong = refs.filter((ref) => shown[named[ref]] !== money(plans[ref].monthly));
      }
      if (wrong.length) throw new Error(wrong.map((ref) => `${ref}: ${shown[named[ref]]} ≠ ${money(plans[ref].monthly)}`).join('; '));
    };
    const quotes = spec.plans.filter((p) => p.line === 'medical').map((p) => p.ref);
    let dealId;
    let tierLabel = {};
    const box = (card, row, tier) => card.getByRole('textbox', { name: `${row}: ${tierLabel[tier]}`, exact: true });
    await signIn(ctx);
    await openDeal(ctx);
    await step('GD3 is at checkpoint A: no current plan, no census (seed_golden GD3 resets it)', async () => {
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      tierLabel = (await api(page, base, 'GET', 'meta/')).enrollment.labels;
      const board = await api(page, base, 'GET', `deals/${dealId}/plans/?line=medical`);
      if (board.plans.some((p) => p.role === 'current') || board.enrollment.census) {
        throw new Error('GD3 has moved on: run manage.py seed_golden GD3 first');
      }
    });
    await step('every medical quote prices from the counts typed for the whole line, marked ✎ counts', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: /^Medical/ }).click();
      await page.getByRole('button', { name: 'Summary tiers · On (1)' }).waitFor();
      await priced(key.A.plans, quotes);
      if ((await page.getByText('✎ counts').count()) < quotes.length) throw new Error('a total lacks its ✎ counts mark');
    });
    await step('the counts card shows the whole-line row: 30 · 8 · 6 · 8', async () => {
      await page.getByRole('button', { name: 'Summary tiers · On (1)' }).click();
      const card = page.getByRole('region', { name: 'Summary medical tiers' });
      for (const [tier, n] of Object.entries(spec.line_enrollment.medical)) {
        const value = await box(card, 'Whole line', tier).inputValue();
        if (value !== String(n)) throw new Error(`${tier} reads ${value}`);
      }
      await card.getByRole('button', { name: 'Cancel' }).click();
    });
    const arrive = (ref) => {
      const plan = spec.arrivals.find((p) => p.ref === ref);
      const body = { line: 'medical', role: 'current', carrier: plan.carrier, name: plan.name, values: plan.values };
      return api(page, base, 'POST', `deals/${dealId}/plans/`, { data: body });
    };
    await step('the packet’s first current plan arrives: it and every quote still price (no price vanishes)', async () => {
      await arrive('D');
      await page.reload();
      await page.getByText(named.D, { exact: true }).first().waitFor();
      await priced(key.A_one_current.plans, ['D', ...quotes]);
    });
    await step('a second current plan names the plans that lost their price', async () => {
      await arrive('F');
      await page.reload();
      await page.getByText(/have no price: Medical has 2 current plans/).waitFor();
      await page.getByText(/10 quotes replace no current plan yet/).waitFor();
      const shown = await totals(page);
      const still = key.A_two_current.no_price.filter((ref) => shown[named[ref]] !== '—');
      if (still.length) throw new Error(`still priced: ${still.join(', ')}`);
    });
    await step('“Split the counts →” opens the card on the split, both current plans picked', async () => {
      await page.getByRole('button', { name: 'Split the counts →' }).click();
      await page.getByText(/^Split 30 EE · 8 ES · 6 EC · 8 FAM between the current plans/).waitFor();
      const card = page.getByRole('region', { name: 'Summary medical tiers' });
      for (const ref of ['D', 'F']) {
        const plan = spec.arrivals.find((p) => p.ref === ref);
        for (const [tier, n] of Object.entries(plan.enrollment)) {
          await box(card, `${plan.carrier} · ${plan.name} (current)`, tier).fill(String(n));
        }
      }
      await card.getByRole('button', { name: 'Save counts' }).click();
      await page.getByRole('region', { name: 'Summary medical tiers' }).waitFor({ state: 'detached' });
      await priced(key.A_split.plans, ['D', 'F']);
    });
    await step('a quote told what it replaces prices that plan’s people', async () => {
      const picker = page.getByRole('combobox', { name: `Which current plan ${named.QA1} replaces` });
      const option = await picker.locator('option', { hasText: named.D }).getAttribute('value');
      await picker.selectOption(option);
      await page.waitForTimeout(800);
      await priced(key.A_split.plans, ['QA1']);
    });
    await step('the census of 48 arrives naming both current plans', async () => {
      const csv = Buffer.from(censusCsv(spec.census));
      const file = { name: 'GD3 census walk (synthetic).csv', mimeType: 'text/csv', buffer: csv };
      const doc = await api(page, base, 'POST', `deals/${dealId}/documents/`, { multipart: { file, kind: 'census' } });
      const imp = await api(page, base, 'POST', `deals/${dealId}/census/imports/`, { data: { document_id: doc.id } });
      await api(page, base, 'POST', `census/imports/${imp.id}/apply/`, { data: {} });
    });
    await step('the Advisor re-prices them: “Priced from the census now · Keep my typed counts”', async () => {
      await page.reload();
      await page.getByText('Priced from the census now').waitFor();
      await page.getByRole('button', { name: 'Keep my typed counts' }).waitFor();
      await priced(key.B.plans, ['D', 'F', 'QA1']);
    });
    await step('counts typed after the import win again', async () => {
      await page.getByRole('button', { name: /^Summary tiers/ }).click();
      const card = page.getByRole('region', { name: 'Summary medical tiers' });
      await card.getByText('Priced from the census now').waitFor();
      const d = spec.arrivals.find((p) => p.ref === 'D');
      await box(card, `${d.carrier} · ${d.name} (current)`, 'EE').fill('17');
      await card.getByRole('button', { name: 'Save counts' }).click();
      await card.waitFor({ state: 'detached' });
      await priced({ D: { monthly: 35049 } }, ['D']); // 17×702.40 + 5×1474.95 + 4×1299.45 + 5×2107.20 = 35,049.35
      await priced(key.A_split.plans, ['F']); // one save stamps the line's typed set: F's counts win again too
      if (await page.getByText('Priced from the census now').count()) throw new Error('the census notice stayed');
    });
  },
};
