// Slice 23's "done when" (plan.md §13.7 row 23; E60–E68, D125, D127, D129): "In Review mode a click jumps the file to
// its value; Ctrl+F walks every match". Run it with `--need s23`. On GD1's Documents tab it opens the Cigna quote on
// the Grid, turns Review mode on and clicks a rate: the workbook rings the cell and the file bar names the value; an
// arrow moves on and the file follows. On 📚 All proposals a renewal's rate opens the Aetna PDF on its page while the
// Grid stays on both files. Then Ctrl+F lands in the find box, and Enter steps through every match and round again.
// It reads only: nothing is written, so GD1 stays as seeded.

const money = (raw) => `$${Number(raw).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const exact = (text) => new RegExp(`^${text.replace(/[$.*+?^(){}|[\]\\]/g, '\\$&')}$`);

export const documents23 = {
  title: 'Slice 23: in Review mode a click jumps the file to its value; Ctrl+F walks every match (E60–E68, D125, D127)',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const ref = (key) => spec.plans.find((plan) => plan.ref === key);
    const cg2 = ref('CG2');
    const a2 = ref('A2');
    const fileBar = page.getByText(/^Opened to show /);
    const findBox = page.getByRole('textbox', { name: 'Find in the scanned data' });
    const where = page.getByRole('status').filter({ hasText: /^(\d+ of \d+|No matches)$/ });
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Documents tab opens on the Cigna quote, shown as the Grid', async () => {
      await page.getByRole('link', { name: 'Documents', exact: true }).click();
      await page.getByRole('tab', { name: /Cigna medical quote/ }).click();
      await page.getByRole('button', { name: '▦ Grid' }).click();
      await page.getByRole('columnheader', { name: /Benefit/ }).waitFor();
    });
    await step('Review mode turns on', async () => {
      const review = page.getByRole('button', { name: /Review$/ });
      if ((await review.getAttribute('aria-pressed')) !== 'true') await review.click();
      await page.getByText('Click finds in file').first().waitFor();
    });
    await step(`a click on ${cg2.name}'s EE rate jumps the workbook to its cell`, async () => {
      await page.getByRole('cell', { name: exact(money(cg2.values.rate_ee)) }).first().click();
      await page.getByText(`Opened to show Rate — EE · Cigna ${cg2.name}`).waitFor();
      await page.getByText(/^Found in .Medical. [A-Z]+\d+$/).waitFor();
    });
    await step('an arrow moves to the next value and the file follows it', async () => {
      await page.keyboard.press('ArrowDown');
      await page.getByText(`Opened to show Rate — EE + Spouse · Cigna ${cg2.name}`).waitFor();
    });
    await step(`on 📚 All proposals a click on ${a2.name}'s renewal rate opens the Aetna PDF on its page`, async () => {
      await page.getByRole('tab', { name: /All proposals/ }).click();
      await page.getByText(/· all 2 files/).waitFor();
      await page.getByRole('cell', { name: exact(money(a2.values.rate_ee)) }).first().click();
      await page.getByText(`Opened to show Rate — EE · Aetna ${a2.name}`).waitFor();
      await page.getByText(/page 2 of 2/).waitFor();
      await page.getByText(/· all 2 files/).waitFor(); // the Grid stays on both files
    });
    let total = 0;
    await step('Ctrl+F lands in the find box, and "hdhp" marks its matches', async () => {
      await page.getByRole('columnheader', { name: /Benefit/ }).click();
      await page.keyboard.press('Control+f');
      if (!(await findBox.evaluate((el) => el === document.activeElement))) throw new Error('Ctrl+F did not land in the box');
      await page.keyboard.type('hdhp');
      await where.filter({ hasText: /^1 of \d+$/ }).waitFor();
      total = Number((await where.innerText()).split(' of ')[1]);
      if (total < 2) throw new Error(`only ${total} match`);
    });
    await step('Enter walks every match, and round to the first again', async () => {
      for (let at = 2; at <= total + 1; at += 1) {
        await findBox.press('Enter');
        const want = at > total ? 1 : at;
        await where.filter({ hasText: new RegExp(`^${want} of ${total}$`) }).waitFor();
      }
    });
    await step('Shift+Enter steps back, and Esc leaves the search', async () => {
      await findBox.press('Shift+Enter');
      await where.filter({ hasText: new RegExp(`^${total} of ${total}$`) }).waitFor();
      await findBox.press('Escape');
      if ((await findBox.inputValue()) !== '') throw new Error('the box kept its words');
    });
  },
};
