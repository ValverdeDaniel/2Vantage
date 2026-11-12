// Need 2, read SBCs and carrier quotes with Work with Claude (plan.md §13.7 row 22, "done when"; V.2 need 2; D38, D47,
// D93, E77, F66; Q.9 row 22; OQ33): on GD3 the renewal packet's read is used (its plans carry Claude's values), then
// "Attach SBC…" on the current BlueOptions PPO 2500 reads a SYNTHETIC SBC made here: the read waits for review even for
// an admin, stages design values only, and the PCP copay it prints differently from the packet lands flagged. Then
// "✦ Ask Claude to re-check" reads the flagged value again; nothing changes until the person applies the re-check.
//
// Run it with `--need 2` on a freshly seeded GD3 (`manage.py seed_golden GD3`). It makes up to THREE REAL Claude calls
// (Sonnet 5.5, about $0.10 of the build's $20 cap, `manage.py ai_spend`): the packet (skipped when a read of it waits),
// the SBC and the re-check. The backend needs ANTHROPIC_API_KEY and the worker must be running. Re-seed GD3 after.

import { pdf } from './syntheticPdf.mjs';

const READ_MS = 300000; // a real read takes about a minute

function sbcFile(carrier, name) {
  const at = (y, text, size = 9, bold = false) => [40, y, text, size, bold];
  const page = [
    at(750, 'Summary of Benefits and Coverage: What this Plan Covers & What You Pay for Covered Services', 11, true),
    at(734, `${carrier}: ${name}          Coverage Period: 01/01/2027 - 12/31/2027`, 10, true),
    at(720, 'Coverage for: Individual + Family | Plan Type: PPO | Network: BlueOptions'),
    at(706, 'SYNTHETIC document made for software testing: not a real plan, carrier filing or member record.', 8),
    at(684, 'Important Questions', 10, true),
    at(668, 'What is the overall deductible?  $2,500 individual / $5,000 family in-network; $5,000 / $10,000 out-of-network.'),
    at(656, 'Each family member meets their own individual deductible until the family deductible is met.'),
    at(640, 'What is the out-of-pocket limit for this plan?  $6,350 individual / $12,700 family in-network.'),
    at(616, 'Common Medical Event | Services You May Need | In-Network Provider | Out-of-Network Provider', 10, true),
    at(600, "If you visit a health care provider's office: Primary care visit | $35 copay/visit | 40% coinsurance"),
    at(586, 'Specialist visit | $60 copay/visit | 40% coinsurance'),
    at(572, 'If you have a test: Diagnostic test (x-ray, blood work) | 20% coinsurance | 40% coinsurance'),
    at(558, 'If you need immediate medical attention: Emergency room care | $350 copay/visit | $350 copay/visit'),
    at(544, 'Urgent care | $75 copay/visit | 40% coinsurance'),
    at(530, 'If you need drugs: Generic drugs | $10 copay | Not covered'),
    at(516, 'Preferred brand drugs | $40 copay | Not covered'),
    at(502, 'Non-preferred brand drugs | $70 copay | Not covered'),
  ];
  return { name: 'BlueOptions PPO 2500 SBC (synthetic).pdf', mimeType: 'application/pdf', buffer: pdf([page]) };
}

export const sbc22 = {
  title: 'Read an SBC with Work with Claude: Attach SBC… stages design values, the disagreement is flagged, a re-check waits for a person (D38, D47, D93, E77)',
  deal: 'GD3',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const plan = spec.arrivals[0];
    const carrier = spec.renewal_packet.carrier;
    await signIn(ctx);
    await openDeal(ctx);

    const menu = page.getByRole('button', { name: `Actions for ${carrier} — ${plan.name}` }).first();
    await step('the renewal packet’s read is used (read now when none waits): its plans carry Claude’s values', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      try {
        await menu.waitFor({ timeout: 8000 });
        return; // used already (a walk run before, or need 1 / 3)
      } catch {
        // not on the deal yet: use the packet's read
      }
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
      await page.getByRole('button', { name: 'Use this scan ▸' }).click();
      await page.getByText('✓ Used Claude’s read — 2 current plans · 2 renewals').waitFor({ timeout: 30000 });
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
    });
    await step(`the Advisor: "Attach SBC…" on ${plan.name} uploads its SBC, and Work with Claude reads it`, async () => {
      await menu.click();
      const [chooser] = await Promise.all([
        page.waitForEvent('filechooser'),
        page.getByRole('menuitem', { name: 'Attach SBC…' }).click(),
      ]);
      await chooser.setFiles(sbcFile(carrier, plan.name));
      await page.getByText(/Reading the SBC for .*review it before it changes the plan/).waitFor();
    });
    await step('the SBC read waits for review, even an admin’s (OQ33): design values, the disagreement flagged', async () => {
      const card = page.locator('[data-review-job]').filter({ hasText: `SBC: ${carrier}` }).first();
      await card.waitFor({ timeout: READ_MS });
      await card.getByText('⚑ lands flagged to review').first().waitFor();
      const text = await card.innerText();
      if (/Rate —|Monthly rates/.test(text)) throw new Error('the SBC read staged a rate');
      if (!/was \$?30/.test(text)) throw new Error('the PCP copay the packet read is not shown as replaced');
    });
    await step('"Use this scan ▸" lands it: the Advisor counts the flagged value to review', async () => {
      await page.getByRole('button', { name: 'Use this scan ▸' }).first().click();
      await page.getByText(/Scan applied — values on 1 plan/).waitFor({ timeout: 30000 });
      await page.keyboard.press('Escape');
      await page.getByText(/AI values? to review/).first().waitFor({ timeout: 30000 });
    });
    await step('"✦ Ask Claude to re-check" proposes; nothing changes until the person applies it', async () => {
      await page.getByRole('button', { name: '✦ Ask Claude to re-check' }).first().click();
      const card = page.locator('[data-recheck-job]').first();
      await card.waitFor({ timeout: READ_MS });
      await card.getByText(/Nothing has changed yet/).waitFor();
      await page.keyboard.press('Escape');
      await page.getByText(/AI values? to review/).first().waitFor(); // still flagged: the re-check only proposes
    });
    await step('Apply: the re-check lands as the person’s, with ↶ Undo this run', async () => {
      await page.getByRole('button', { name: /✦ Claude|Work with Claude/ }).first().click();
      const card = page.locator('[data-recheck-job]').first();
      await card.getByRole('button', { name: /^Apply \d+ selected ▸$/ }).click();
      await page.getByText(/✓ Applied Claude’s re-check|Applied — /).first().waitFor({ timeout: 30000 });
    });
  },
};
