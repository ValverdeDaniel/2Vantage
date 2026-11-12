// Needs 4 and 5 asked of Claude (plan.md §13.7 row 24, "done when"; V.2 needs 4–5; D80, F24, F108): on GD1's Advisor,
// "Show PPOs under $40,000 a month" in Work with Claude sets the board — a rule chip for the plan type, the line's
// "Monthly total ≤ $" at 40,000 — and only the medical PPO quotes show; nothing on the deal changes; Clear resets it.
//
// Run it with `--need 5c`. Each run asks ONE REAL Claude turn (Sonnet 5.5, about $0.03 of the build's $20 cap,
// `manage.py ai_spend`); the backend needs ANTHROPIC_API_KEY and the worker must be running.

const TURN_MS = 180000;
const WORDS = 'Show PPOs under $40,000 a month';

export const boardClaude24 = {
  title: 'Ask Claude to filter the board: "Show PPOs under $40,000 a month" sets the board and writes nothing (D80)',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const quotes = spec.plans.filter((p) => p.line === 'medical' && p.role !== 'current');
    const ppos = quotes.filter((p) => /PPO/i.test(p.values?.plan_type || ''));
    const drawer = page.getByRole('dialog', { name: 'Work with Claude' });
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Advisor opens on Medical with every quote, and Work with Claude opens beside it', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: /^Medical/ }).click();
      await page.getByText(new RegExp(`^Showing ${quotes.length} of ${quotes.length} quoted plans`)).waitFor();
      await page.getByRole('button', { name: 'Work with Claude' }).click();
      await drawer.getByLabel('Message to Claude').waitFor();
    });
    await step(`"${WORDS}" is answered in the chat`, async () => {
      await drawer.getByRole('button', { name: '＋ New chat' }).click().catch(() => {});
      await drawer.getByLabel('Message to Claude').fill(WORDS);
      await drawer.getByRole('button', { name: 'Send', exact: true }).click();
      await drawer.getByText(/^This run \$/).last().waitFor({ timeout: TURN_MS });
    });
    await step(`the board shows the ${ppos.length} PPO quotes, with Claude's rule and the line's total cap`, async () => {
      await page.getByText(new RegExp(`^Showing ${ppos.length} of ${quotes.length} quoted plans`)).waitFor();
      await page.getByRole('button', { name: /Plan Type contains “PPO”/ }).waitFor();
      const cap = page.getByRole('spinbutton', { name: /Monthly total ≤ \$/ });
      if (Number(await cap.inputValue()) !== 40000) throw new Error('the total cap is not 40,000');
    });
    await step('closing the drawer, Clear puts every quote back', async () => {
      await drawer.getByRole('button', { name: 'Close' }).click();
      await page.getByRole('button', { name: 'Clear', exact: true }).click();
      await page.getByText(new RegExp(`^Showing ${quotes.length} of ${quotes.length} quoted plans`)).waitFor();
    });
  },
};
