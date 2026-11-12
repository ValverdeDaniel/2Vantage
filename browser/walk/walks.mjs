// The Walk lane's scripts (plan.md §12.5, Q.2; V.2's twelve needs and each slice's "done when"). A walk does what a
// person does in Chrome and finds everything by role and visible words, never by class or id, so it survives the
// restyling slices. Each walk: { title, deal, run(ctx) }, where ctx = { page, step, base, user, spec }.
// Needs 1–12 arrive with the slices that build them (Q.9); 0 is the example the lane started with.

import { archive38 } from './archive38.mjs';
import { asQuoted21 } from './asQuoted21.mjs';
import { boardClaude24 } from './boardClaude24.mjs';
import { builder25 } from './builder25.mjs';
import { builder26 } from './builder26.mjs';
import { census41 } from './census41.mjs';
import { documents23 } from './documents23.mjs';
import { documents65 } from './documents65.mjs';
import { export28 } from './export28.mjs';
import { intake39 } from './intake39.mjs';
import { market40 } from './market40.mjs';
import { pages14 } from './pages14.mjs';
import { pdf29 } from './pdf29.mjs';
import { questionnaire42 } from './questionnaire42.mjs';
import { questionnaire43 } from './questionnaire43.mjs';
import { rfp44 } from './rfp44.mjs';
import { review53 } from './review53.mjs';
import { pptx31 } from './pptx31.mjs';
import { sbc22 } from './sbc22.mjs';
import { quoteDoor20 } from './quoteDoor20.mjs';
import { quoteFirst13 } from './quoteFirst13.mjs';
import { scanQuotes19 } from './scanQuotes19.mjs';

const signIn = async ({ page, step, base, user }) => {
  await step('the sign-in page asks for a username and password', async () => {
    await page.goto(`${base}/login`);
    await page.getByLabel('Username').fill(user.name);
    await page.getByLabel('Password').fill(user.password);
  });
  await step('signing in lands on the client list', async () => {
    await page.getByRole('button', { name: /sign in|log in/i }).click();
    await page.getByLabel(/search clients/i).waitFor();
  });
};

const openDeal = async ({ page, step, spec }) => {
  await step(`searching "${spec.client}" finds the deal`, async () => {
    await page.getByLabel(/search clients/i).fill(spec.client);
    await page.getByRole('link', { name: spec.client }).first().click();
    await page.waitForURL(/\/deals\/\d+/);
  });
};

export const WALKS = {
  0: {
    title: "Example: sign in and open GD1's Advisor",
    deal: 'GD1',
    async run(ctx) {
      const { page, step, spec } = ctx;
      await signIn(ctx);
      await openDeal(ctx);
      await step('the Advisor tab opens', async () => {
        await page.getByRole('link', { name: 'Advisor', exact: true }).click();
        await page.waitForURL(/\/deals\/\d+\/advisor/);
      });
      await step("the Advisor shows the deal's current medical plans", async () => {
        const currents = spec.plans.filter((p) => p.line === 'medical' && p.role === 'current');
        // Visible text only: the board's "Replacing:" pickers list the current plans in their (hidden) options too.
        for (const plan of currents) {
          await page.getByText(plan.name, { exact: false }).filter({ visible: true }).first().waitFor();
        }
      });
    },
  },
  1: { ...scanQuotes19, run: (ctx) => scanQuotes19.run(ctx, { signIn, openDeal }) }, // scan quotes; slice 19 (one real read)
  '1q': { ...quoteDoor20, run: (ctx) => quoteDoor20.run(ctx, { signIn }) }, // need 1 by the quote-first door; slice 20 (one real read)
  '5c': { ...boardClaude24, run: (ctx) => boardClaude24.run(ctx, { signIn, openDeal }) }, // needs 4–5 asked of Claude; slice 24 (one real turn)
  2: { ...sbc22, run: (ctx) => sbc22.run(ctx, { signIn, openDeal }) }, // SBCs and the re-check; slice 22 (up to 3 real calls)
  3: { ...asQuoted21, run: (ctx) => asQuoted21.run(ctx, { signIn, openDeal }) }, // "As quoted"; slice 21 (a real read only when none waits)
  4: {
    title: 'Search plans by name: "UHC" finds the UnitedHealthcare quotes on every line (F14–F17, OQ14)',
    deal: 'GD1',
    async run(ctx) {
      const { page, step, spec } = ctx;
      const quotes = spec.plans.filter((p) => p.line === 'medical' && p.role !== 'current');
      const uhc = quotes.filter((p) => /^UnitedHealthcare/.test(p.carrier));
      const medical = spec.plans.filter((p) => p.line === 'medical');
      const unique = (p) => !medical.some((q) => q !== p && (q.name.includes(p.name) || p.name.includes(q.name)));
      const others = quotes.filter((p) => !/^UnitedHealthcare/.test(p.carrier) && unique(p));
      const finder = page.getByRole('textbox', { name: /Find a plan/ });
      const count = page.getByText(/^Showing \d+ of \d+ quoted plans/);
      await signIn(ctx);
      await openDeal(ctx);
      await step('the Advisor opens on the medical board with its finder', async () => {
        await page.getByRole('link', { name: 'Advisor', exact: true }).click();
        await page.getByRole('button', { name: /^Medical/ }).click();
        await finder.waitFor();
      });
      await step(`"UHC" leaves the ${uhc.length} UnitedHealthcare quotes, by their carrier's nickname`, async () => {
        await finder.fill('UHC');
        await page.getByText(new RegExp(`^Showing ${uhc.length} of ${quotes.length} quoted plans`)).waitFor();
        for (const plan of uhc) await page.getByRole('row', { name: new RegExp(plan.name) }).first().waitFor();
        const hidden = others[0];
        if (await page.getByRole('row', { name: new RegExp(hidden.name) }).count()) {
          throw new Error(`${hidden.carrier} ${hidden.name} still shows`);
        }
      });
      await step('the words stay in the address, so a reload keeps the search', async () => {
        await page.reload();
        await page.getByText(new RegExp(`^Showing ${uhc.length} of`)).waitFor();
        if ((await finder.inputValue()) !== 'UHC') throw new Error('the finder lost its words');
      });
      await step('on Dental nothing matches, and the board says where the matches are', async () => {
        await page.getByRole('button', { name: /^Dental/ }).click();
        await page.getByText(`Nothing on Dental matches “UHC”, but ${uhc.length} plans on Medical do.`, { exact: false }).waitFor();
      });
      await step(`"Also matches ${uhc.length} on Medical" switches back and keeps the words`, async () => {
        await page.getByRole('button', { name: `${uhc.length} on Medical` }).click();
        await page.getByText(new RegExp(`^Showing ${uhc.length} of ${quotes.length}`)).waitFor();
        if ((await finder.inputValue()) !== 'UHC') throw new Error('the words were lost');
      });
      await step('Escape clears the finder and every quote shows again', async () => {
        await finder.press('Escape');
        await page.getByText(new RegExp(`^Showing ${quotes.length} of ${quotes.length}`)).waitFor();
        await count.waitFor();
      });
    },
  },
  5: {
    title: 'Filter by budget against the monthly total row: "Monthly total ≤ $" and the budget select (F18, F19, F140)',
    deal: 'GD1',
    async run(ctx) {
      const { page, step, spec } = ctx;
      const quotes = spec.plans.filter((p) => p.line === 'medical' && p.role !== 'current');
      const cap = page.getByRole('spinbutton', { name: /Monthly total ≤ \$/ });
      const showing = (n) => page.getByText(new RegExp(`^Showing ${n} of \\d+ quoted plans`)).waitFor();
      const money = (text) => Number(String(text).replace(/[^0-9.-]/g, ''));
      let totals = [];
      await signIn(ctx);
      await openDeal(ctx);
      await step('the Advisor opens on the medical board', async () => {
        await page.getByRole('link', { name: 'Advisor', exact: true }).click();
        await page.getByRole('button', { name: /^Medical/ }).click();
        await cap.waitFor();
      });
      await step("the board's Monthly total column gives every quote's total", async () => {
        const heads = await page.getByRole('columnheader').allInnerTexts();
        const at = heads.findIndex((text) => /Monthly total/i.test(text));
        const rows = page.getByRole('row').filter({ hasNotText: /CURRENT/ }).filter({ has: page.getByRole('cell') });
        totals = (await rows.evaluateAll((trs, i) => trs.map((tr) => tr.cells[i]?.innerText ?? ''), at)).map(money);
        if (totals.length !== quotes.length) throw new Error(`${totals.length} quote rows, ${quotes.length} in the spec`);
      });
      await step('"Monthly total ≤ $45,000" keeps every quote at or under it', async () => {
        await cap.fill('45000');
        await showing(totals.filter((t) => t <= 45000).length);
      });
      await step('a lower cap hides the dearer plans and keeps the cheaper ones', async () => {
        const sorted = [...totals].sort((a, b) => a - b);
        const limit = sorted[Math.floor(sorted.length / 2)];
        await cap.fill(String(limit));
        await showing(totals.filter((t) => t <= limit).length);
      });
      await step('a quote with no total yet is named, never hidden silently', async () => {
        await page.getByRole('button', { name: '✎ Edit' }).click();
        await page.getByRole('button', { name: '＋ Add plan' }).click();
        const dialog = page.getByRole('dialog', { name: 'Add a plan' });
        await dialog.getByLabel('Carrier').fill('Walk Carrier (synthetic)');
        await dialog.getByLabel('Plan name').fill('Walk 5 unpriced quote');
        await dialog.getByRole('button', { name: 'Add plan' }).click();
        await page.getByRole('button', { name: 'Done ✓' }).click();
        await page.getByText(/1 has no price yet — .*: Walk Carrier \(synthetic\) Walk 5 unpriced quote/).waitFor();
      });
      await step('the quote added for the walk is removed again', async () => {
        await page.getByRole('button', { name: 'Clear', exact: true }).click();
        await page.getByRole('button', { name: /Actions for Walk Carrier \(synthetic\)/ }).click();
        await page.getByRole('menuitem', { name: 'Delete…' }).click();
        await page.getByRole('alertdialog').or(page.getByRole('dialog')).getByRole('button', { name: 'Remove', exact: true }).click();
        await showing(quotes.length);
      });
      await step('"Within 5% of current" keeps the quotes at most 5% above what they replace', async () => {
        await page.getByRole('combobox', { name: 'Budget' }).selectOption({ label: 'Within 5% of current' });
        const heads = await page.getByRole('columnheader').allInnerTexts();
        const at = heads.findIndex((text) => /Δ vs current/i.test(text));
        await page.waitForTimeout(300);
        const rows = page.getByRole('row').filter({ hasNotText: /CURRENT/ }).filter({ has: page.getByRole('cell') });
        const deltas = await rows.evaluateAll((trs, i) => trs.map((tr) => tr.cells[i]?.innerText ?? ''), at);
        const over = deltas.filter((text) => Number(text.replace('−', '-').replace(/[^0-9.-]/g, '')) > 5);
        if (!deltas.length || over.length) throw new Error(`Δ shown: ${deltas.join(', ')}`);
      });
    },
  },
  6: { ...quoteFirst13, run: (ctx) => quoteFirst13.run(ctx, { signIn, openDeal }) }, // quote-first; slice 13's done-when
  8: { ...pages14[8], run: (ctx) => pages14[8].run(ctx, { signIn, openDeal }) }, // Replacing: on ▦ Pages; slice 14
  9: { ...pages14[9], run: (ctx) => pages14[9].run(ctx, { signIn, openDeal }) }, // slot picks on ▦ Pages; slice 14
  10: {
    title: "Transpose the table: GD1's medical board as plans-as-columns, header frozen, kept per browser (F34, F35)",
    deal: 'GD1',
    async run(ctx) {
      const { page, step, spec } = ctx;
      await signIn(ctx);
      await openDeal(ctx);
      await step('the Advisor opens on the medical board', async () => {
        await page.getByRole('link', { name: 'Advisor', exact: true }).click();
        await page.getByRole('button', { name: /^Medical/ }).click();
        await page.getByRole('button', { name: '⇄ Transpose' }).waitFor();
      });
      const currents = spec.plans.filter((p) => p.line === 'medical' && p.role === 'current');
      await step('⇄ Transpose turns the plans into columns (every column of the line as a row)', async () => {
        await page.getByRole('button', { name: 'All columns' }).click();
        await page.getByRole('button', { name: '⇄ Transpose' }).click();
        await page.getByRole('columnheader', { name: /Benefit/ }).waitFor();
        for (const plan of currents) {
          await page.getByRole('columnheader', { name: new RegExp(plan.name, 'i') }).first().waitFor();
        }
        await page.getByRole('cell', { name: /^Monthly total/ }).waitFor();
      });
      await step('the header row stays put while the table scrolls under it', async () => {
        const head = page.getByRole('columnheader', { name: /Benefit/ });
        const row = page.getByRole('cell', { name: /^Plan Type/ });
        await row.hover();
        const before = [await head.boundingBox(), await row.boundingBox()];
        await page.mouse.wheel(0, 300);
        await page.waitForTimeout(400);
        const after = [await head.boundingBox(), await row.boundingBox()];
        if (Math.abs(after[0].y - before[0].y) > 1) throw new Error(`the header moved ${before[0].y} → ${after[0].y}`);
        if (after[1].y >= before[1].y) throw new Error('the table did not scroll');
      });
      await step('the choice is kept in this browser', async () => {
        await page.reload();
        await page.getByRole('columnheader', { name: /Benefit/ }).waitFor();
      });
      await step('⇄ Transpose again puts the plans back in rows', async () => {
        await page.getByRole('button', { name: '⇄ Transpose' }).click();
        await page.getByRole('columnheader', { name: /Monthly total/i }).waitFor();
        await page.getByRole('row', { name: new RegExp(currents[0].name) }).first().waitFor();
      });
    },
  },
  s39: { ...intake39, run: (ctx) => intake39.run(ctx, { signIn, openDeal }) }, // slice 39's done-when
  s23: { ...documents23, run: (ctx) => documents23.run(ctx, { signIn, openDeal }) }, // slice 23's done-when
  s41: { ...census41, run: (ctx) => census41.run(ctx, { signIn, openDeal }) }, // slice 41's done-when
  s65: { ...documents65, run: (ctx) => documents65.run(ctx, { signIn, openDeal }) }, // slice 65's done-when
  s25: { ...builder25, run: (ctx) => builder25.run(ctx, { signIn, openDeal }) }, // slice 25's done-when
  s26: { ...builder26, run: (ctx) => builder26.run(ctx, { signIn, openDeal }) }, // slice 26's done-when
  s29: { ...pdf29, run: (ctx) => pdf29.run(ctx, { signIn, openDeal }) }, // slice 29's done-when
  s31: { ...pptx31, run: (ctx) => pptx31.run(ctx, { signIn, openDeal }) }, // slice 31's done-when
  11: { ...export28, run: (ctx) => export28.run(ctx, { signIn, openDeal }) }, // the Export viewer; slice 28's done-when
  s38: { ...archive38, run: (ctx) => archive38.run(ctx, { signIn, openDeal }) }, // slice 38's done-when
  s40: { ...market40, run: (ctx) => market40.run(ctx, { signIn, openDeal }) }, // slice 40's done-when
  s42: { ...questionnaire42, run: (ctx) => questionnaire42.run(ctx, { signIn, openDeal }) }, // slice 42's done-when
  s43: { ...questionnaire43, run: (ctx) => questionnaire43.run(ctx, { signIn, openDeal }) }, // slice 43's done-when
  s44: { ...rfp44, run: (ctx) => rfp44.run(ctx, { signIn, openDeal }) }, // slice 44's done-when (re-seed GD2 after)
  s53: { ...review53, run: (ctx) => review53.run(ctx, { signIn, openDeal }) }, // slice 53's done-when (re-seed GD4 after)
};
