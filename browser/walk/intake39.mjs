// Slice 39's "done when" (plan.md §13.9 row 39; B1–B9, F139): on GD6 all four cards fill by keyboard; a bad FEIN
// shows its message; "Client target $X/mo · Apply" appears on the Advisor. Run it with `--need s39`.
//
// The walk empties GD6's form through the API first (a fresh intake), then types every answer of the spec with the
// keyboard only: one click opens Legal Company Name, and from there each answer is typed and Enter goes on (a select
// takes its option by typing, a date its digits, a multi its codes). It reads the stored answers back against GD6's
// hand-worked key. It leaves GD6 as the spec has it; `seed_golden GD6` resets it anyway.

import { answerKey } from '../shared/golden.mjs';

const SECTIONS = ['Employer information', 'Eligibility & workforce', 'Goals & preferences', 'Compliance & regulatory'];

async function api(page, base, method, url, data) {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
  const response = await page.request.fetch(`${base}/api/${url}`, {
    method,
    data,
    headers: { 'X-CSRFToken': csrf, Referer: base },
  });
  if (!response.ok()) throw new Error(`${method} ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

/** A question's answer on the form, which a click opens. */
function answerOf(page, label) {
  return page.getByRole('button', { name: `Edit ${label}`, exact: true });
}

/** What a person types for one answer: a date's digits (mm dd yyyy), a list's codes, anything else as written. */
function keystrokes(question, raw) {
  if (question.type === 'date') {
    const [m, d, y] = String(raw).split('/');
    return `${m.padStart(2, '0')}${d.padStart(2, '0')}${y}`;
  }
  return Array.isArray(raw) ? raw.join(', ') : String(raw);
}

export const intake39 = {
  title: 'Slice 39: GD6’s four intake cards fill by keyboard; a bad FEIN shows its message; the Advisor shows the client’s budget',
  deal: 'GD6',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec, base } = ctx;
    const key = answerKey('GD6').intake;
    const answers = spec.intake.answers;
    let dealId;
    let order = [];
    await signIn(ctx);
    await openDeal(ctx);
    await step('the walk empties GD6’s form through the API (a fresh intake)', async () => {
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      const meta = await api(page, base, 'GET', 'meta/');
      const { sections, guidance } = meta.intake.form;
      order = sections.flatMap((section) => [...section.questions, ...(guidance.section === section.key ? [guidance] : [])]);
      const blank = Object.fromEntries(Object.keys(answers).map((k) => [k, '']));
      await api(page, base, 'PATCH', `deals/${dealId}/intake/`, { answers: blank });
    });
    await step('the Intake tab shows the four cards, every needed question Missing', async () => {
      await page.getByRole('link', { name: 'Intake', exact: true }).click();
      for (const title of SECTIONS) await page.getByText(title, { exact: true }).waitFor();
      await page.getByText('Required to market').waitFor();
    });
    const shown = [...order.filter((q) => !key.hidden.includes(q.key))];
    const reached = (label) =>
      page
        .waitForFunction((name) => document.activeElement?.getAttribute('aria-label') === name, label, { timeout: 10000 })
        .catch(() => {
          throw new Error(`Enter did not reach ${label}`);
        });
    await step('one click opens Legal Company Name; then every answer is typed and Enter goes on, card by card', async () => {
      await answerOf(page, 'Legal Company Name').click();
      for (const question of shown) {
        await reached(question.label);
        if (question.key in answers) await page.keyboard.type(keystrokes(question, answers[question.key]), { delay: 5 });
        await page.keyboard.press('Enter');
      }
      await reached('Legal Company Name'); // the last Enter wraps to the top
      await page.keyboard.press('Escape');
    });
    await step('every card holds what was typed, stored as GD6’s key says', async () => {
      await page.waitForTimeout(1500); // the last saves land
      const body = await api(page, base, 'GET', `deals/${dealId}/intake/`);
      const wrong = Object.entries(key.stored).filter(([k, v]) => JSON.stringify(body.answers[k]) !== JSON.stringify(v));
      if (wrong.length) throw new Error(`stored differently: ${wrong.map(([k]) => k).join(', ')}`);
      const unanswered = shown.filter((q) => q.key in answers && [undefined, '', null].includes(body.answers[q.key]));
      if (unanswered.length) throw new Error(`left blank: ${unanswered.map((q) => q.key).join(', ')}`);
      if (JSON.stringify(body.readiness) !== JSON.stringify(key.readiness)) throw new Error(JSON.stringify(body.readiness));
      if (await page.getByText('Required to market').count()) throw new Error('the banner still asks for answers');
    });
    await step('a bad FEIN shows its message and keeps the stored one', async () => {
      await page.keyboard.press('Escape');
      await answerOf(page, 'FEIN').click();
      await page.keyboard.press('Control+A');
      await page.keyboard.type('12-345');
      await page.keyboard.press('Enter');
      await page.getByText('FEIN takes XX-XXXXXXX, not "12-345"').waitFor();
      await page.keyboard.press('Escape');
      await answerOf(page, 'FEIN').getByText(key.stored.fein).waitFor();
    });
    await step('typing a good FEIN clears the message', async () => {
      await answerOf(page, 'FEIN').click();
      await page.keyboard.press('Control+A');
      await page.keyboard.type(key.stored.fein);
      await page.keyboard.press('Enter');
      await page.getByText('FEIN takes XX-XXXXXXX').waitFor({ state: 'detached' });
    });
    await step('the Advisor’s filter card shows “Client target $62,000/mo · Apply”', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click(); // GD6 quotes medical only: no line tabs
      await page.getByText(`Client target $${key.budget_hints.target_monthly.toLocaleString('en-US')}/mo`).waitFor();
      await page.getByText(`Client accepts up to ${key.budget_hints.accepts_up_to_pct}%`).waitFor();
    });
    await step('Apply sets “Monthly total ≤ $” to the target, and the hint stays', async () => {
      await page.getByRole('button', { name: 'Apply' }).first().click();
      const cap = page.getByRole('spinbutton', { name: /Monthly total ≤ \$/ });
      const wanted = String(key.budget_hints.target_monthly);
      for (let tries = 0; (await cap.inputValue()) !== wanted; tries += 1) {
        if (tries > 20) throw new Error(`the cap reads "${await cap.inputValue()}", not ${wanted}`);
        await page.waitForTimeout(250);
      }
      await page.getByText(/^Showing 1 of 2 quoted plans/).waitFor(); // only Aetna's $60,200 is under $62,000
      await page.getByText(/Client target \$62,000\/mo/).waitFor();
    });
    await step('the acceptable increase applies the nearest budget step inside it', async () => {
      await page.getByRole('button', { name: 'Apply' }).click();
      const budget = page.getByRole('combobox', { name: 'Budget' });
      const picked = () => budget.evaluate((select) => select.options[select.selectedIndex].text);
      for (let tries = 0; (await picked()) !== 'Within 5% of current'; tries += 1) {
        if (tries > 20) throw new Error(`the budget reads "${await picked()}"`);
        await page.waitForTimeout(250);
      }
      await page.getByRole('button', { name: 'Clear', exact: true }).click();
    });
  },
};
