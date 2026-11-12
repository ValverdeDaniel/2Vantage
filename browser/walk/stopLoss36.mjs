// Slice 36's "done when" (plan.md §13.8 row 36; F98–F104, F29): on GD5, the Advisor's Stop-loss analysis names the
// basis's source, ranks the verdict cards lowest first on the chosen key, keeps the punchline true whatever the rank
// key, and models a dropped laser without saving anything: the deal's Activity is the same after, and a reload shows
// every laser again. The figures are GD5's hand-worked key (golden/keys/gd5.json). Run with `--need s36`.

import { answerKey } from '../shared/golden.mjs';

const money = (text) => (/\$[\d,]+/.test(text) ? Number(text.replace(/[^0-9.-]/g, '')) : null);

export const stopLoss36 = {
  title: 'GD5 stop-loss analysis: the basis names its source, the verdict ranks lowest first, the what-if is never saved',
  deal: 'GD5',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const key = answerKey('GD5').stop_loss;
    const plans = Object.fromEntries(spec.plans.map((p) => [p.ref, p]));
    const words = (ref) => `${plans[ref].carrier} · ${plans[ref].name}`;
    const verdict = () => page.getByRole('list', { name: 'Verdict' });
    const ranked = async () => {
      const items = verdict().getByRole('listitem').filter({ hasText: /^\d/ });
      const out = [];
      for (const item of await items.all()) {
        const name = (await item.getAttribute('aria-label')).replace(/^Rank \d+: /, '');
        out.push({ name, mal: money(await item.getByLabel('Maximum annual liability').innerText()) });
      }
      return out;
    };
    const activity = () =>
      page.evaluate(async () => {
        const id = window.location.pathname.match(/\/deals\/(\d+)/)[1];
        const res = await fetch(`/api/deals/${id}/activity/`, { credentials: 'same-origin' });
        return JSON.stringify(await res.json());
      });
    await signIn(ctx);
    await openDeal(ctx);
    let before = '';
    await step('the Advisor offers "Stop-loss analysis" second, as the deal has a stop-loss line (F2)', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      const pills = page.getByRole('group', { name: 'View' }).getByRole('button');
      await pills.first().waitFor();
      const labels = await pills.allInnerTexts();
      if (labels[1] !== 'Stop-loss analysis') throw new Error(labels.join(' | '));
      before = await activity();
      await page.getByRole('group', { name: 'View' }).getByRole('button', { name: 'Stop-loss analysis' }).click();
    });
    await step(`the basis names its source: "${key.basis.lives} enrolled employees × 12 months … ${key.basis.words}"`, async () => {
      await page.getByText(`${key.basis.lives} enrolled employees × ${key.basis.months} months`, { exact: false }).waitFor();
      await page.getByText(key.basis.words, { exact: false }).first().waitFor();
    });
    await step('the verdict cards rank lowest first on maximum annual liability, the unscored option last', async () => {
      await verdict().waitFor();
      const shown = await ranked();
      const want = key.ranks.max_annual_liability.map(words);
      if (shown.map((card) => card.name).join(' | ') !== want.join(' | ')) throw new Error(JSON.stringify(shown));
      const scored = shown.map((card) => card.mal).filter((mal) => mal != null);
      if (scored.some((mal, i) => i && mal < scored[i - 1])) throw new Error(`not lowest first: ${scored}`);
      if (shown.at(-1).mal != null) throw new Error('the unscored option is not last');
    });
    await step('ranked on Annual SL premium, the cards follow it, and the punchline still names the cheapest premium', async () => {
      await page.getByRole('combobox', { name: /Rank by/ }).selectOption({ label: 'Annual SL premium' });
      await page.getByText('ranked on annual sl premium (lowest wins)', { exact: false }).waitFor();
      const shown = await ranked();
      if (shown.map((card) => card.name).join(' | ') !== key.ranks.annual_premium.map(words).join(' | ')) {
        throw new Error(JSON.stringify(shown));
      }
      await page.getByText(`The lowest premium on this page is ${plans[key.punchline].carrier}`).waitFor();
      await page.getByRole('combobox', { name: /Rank by/ }).selectOption({ label: 'Maximum annual liability' });
    });
    const whatIf = key.what_if;
    const [ref] = Object.keys(whatIf.without);
    const laser = whatIf.without[ref][0];
    await step(`unticking laser ${laser} of ${words(ref)} moves its liability and the ranking, labelled what-if`, async () => {
      await page.getByRole('checkbox', { name: `Include laser ${laser} of ${words(ref)}` }).uncheck();
      await page.getByRole('button', { name: 'Reset lasers' }).waitFor();
      const want = Math.round(Number(whatIf[ref].max_annual_liability));
      await page.waitForFunction(
        ([name, figure]) =>
          [...document.querySelectorAll('[role="listitem"]')].some(
            (item) => item.getAttribute('aria-label')?.endsWith(name) && item.innerText.includes(figure),
          ),
        [words(ref), `$${want.toLocaleString('en-US')}`],
      );
      const shown = await ranked();
      if (shown.map((card) => card.name).join(' | ') !== whatIf.max_annual_liability.map(words).join(' | ')) {
        throw new Error(JSON.stringify(shown));
      }
      await verdict().getByText('what-if').first().waitFor();
    });
    await step('nothing was saved: the Activity is the same, and a reload shows every laser again', async () => {
      if ((await activity()) !== before) throw new Error('the what-if wrote Activity');
      await page.reload();
      await verdict().waitFor();
      const box = page.getByRole('checkbox', { name: `Include laser ${laser} of ${words(ref)}` });
      if (!(await box.isChecked())) throw new Error('the dropped laser stayed dropped');
      const original = Math.round(Number(key.plans[ref].max_annual_liability));
      const card = (await ranked()).find((item) => item.name === words(ref));
      if (card.mal !== original) throw new Error(`${card.mal} != ${original}`);
    });
  },
};
