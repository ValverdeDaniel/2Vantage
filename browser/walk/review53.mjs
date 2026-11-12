// Slice 53's "done when" (plan.md §13.10 row 53; L1, L2, L7, L8, L28, L40, L60, L64, L71): a link is created, copied
// and revoked; the Waiting lane and the pills count it. Run it with `--need s53`. It leaves a request on GD4 (its
// link turned off), so seed GD4 again afterwards (`seed_golden GD4`).
//
// Everything is done on the Review & requests tab: the empty Board, the Request pill's New link (a typed person,
// the intake's blanks and the census file), the floor raising a census-people ask to a PIN, Create link, Copy link
// (the clipboard is read back), the Board's Waiting lane and its count, Turn off and its Undo.

export const review53 = {
  title: 'Slice 53: a link is created, copied and revoked; the Waiting lane and the pills count it',
  deal: 'GD4',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base } = ctx;
    const person = 'Walker Example (synthetic)';
    const lane = () => page.getByRole('region', { name: 'Waiting on the client' });
    const card = () => lane().getByRole('group', { name: `${person}’s link` });
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'], { origin: base });
    await signIn(ctx);
    await openDeal(ctx);
    await step('the sidebar opens Review & requests: the Board, its readiness strip and an empty Waiting lane', async () => {
      await page.getByRole('link', { name: 'Review & requests', exact: true }).click();
      await page.waitForURL(/\/deals\/\d+\/review/);
      await page.getByText('Everything this deal is missing, waiting on and has to review, in one place.').waitFor();
      await page.getByText('intake complete').waitFor();
      await lane().getByText('No request is out.').waitFor();
      await page.getByRole('button', { name: 'Board', exact: true, pressed: true }).waitFor();
      if (!(await page.getByRole('button', { name: /^Review/ }).isDisabled())) throw new Error('Review is offered at 0');
    });
    await step('Request ▸ New link settings: a census-people ask rises to a PIN by itself', async () => {
      await page.getByRole('button', { name: 'Request', exact: true }).click();
      await page.getByRole('group', { name: 'New link settings' }).waitFor();
      await page.getByLabel('Census', { exact: true }).selectOption({ label: 'The required census gaps' });
      await page.getByText('Raised to a PIN because of Census.').waitFor();
      await page.getByLabel('Census', { exact: true }).selectOption({ label: 'Nothing' });
      await page.getByText('Raised to a PIN because of Census.').waitFor({ state: 'detached' });
    });
    await step('a person typed in, the intake’s blanks and their census file: Create link answers "Link ready"', async () => {
      await page.getByLabel('Their name').fill(person);
      await page.getByRole('button', { name: 'Add', exact: true }).click();
      await page.getByLabel('Intake', { exact: true }).selectOption({ label: 'Every blank question' });
      await page.getByRole('checkbox', { name: /Their census file/ }).check();
      await page.getByLabel('A note for them').fill('Thanks — a few things before we go to market.');
      await page.getByRole('button', { name: 'Create link', exact: true }).click();
      await page.getByText(/^Link ready: paste each into your own email/).waitFor();
    });
    await step('Copy link puts the /portal/ URL on the clipboard and marks it sent', async () => {
      await page.getByRole('button', { name: 'Copy link', exact: true }).click();
      await page.getByText('Copied — marked as sent').waitFor();
      const copied = await page.evaluate(() => navigator.clipboard.readText());
      if (!new RegExp(`^${base}/portal/[A-Za-z0-9_-]{43}$`).test(copied)) throw new Error(`copied "${copied}"`);
      await page.getByText('sent', { exact: true }).waitFor();
    });
    await step('Done ▸ the Board: the Waiting lane counts the request, waiting on Walker', async () => {
      await page.getByRole('button', { name: 'Done', exact: true }).click();
      await lane().locator('.bb-nav-badge').getByText('1', { exact: true }).waitFor();
      await lane().getByText('Waiting on them', { exact: true }).waitFor();
      await lane().getByText('The census file', { exact: true }).waitFor();
      await lane().getByText('Intake gaps', { exact: true }).waitFor();
      await lane().getByText('“Thanks — a few things before we go to market.”').waitFor();
      await card().getByText('Waiting', { exact: true }).waitFor();
      await card().getByText(/^sent just now · not opened yet$/).waitFor();
    });
    await step('Turn off: the link stops opening, and the request leaves the lane (0)', async () => {
      await card().getByRole('button', { name: 'Turn off', exact: true }).click();
      await page.getByText(/link is off: what they said stays, and what it asked reads missing · Undo$/).waitFor();
      await lane().getByText('No request is out.').waitFor();
      await lane().locator('.bb-nav-badge').getByText('0', { exact: true }).waitFor();
    });
    await step('Undo turns it back on: the card and its count come back, then it is turned off again', async () => {
      await page.getByRole('button', { name: 'Undo', exact: true }).click();
      await page.getByText('Undone — the link is back on').waitFor();
      await card().getByText('Waiting', { exact: true }).waitFor();
      await card().getByRole('button', { name: 'Turn off', exact: true }).click();
      await lane().getByText('No request is out.').waitFor();
    });
  },
};
