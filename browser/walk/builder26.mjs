// Slice 26's "done when" (plan.md §13.8 row 26; J38–J46, J63–J67): on GD1's Proposal builder every deal card saves
// and marks itself done (an edit takes its own mark off), and Markets checked lists the quoting carriers with "no RFP
// sent". Run with `--need s26`. It puts back each setting and mark it touched (through the same doors), so GD1's
// proposal is left as it found it. Cards are found by their toggle's name ("Collapse How the documents look") and
// their mark's words.

async function api(page, base, url, method = 'GET', body = undefined) {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
  const response = await page.request.fetch(`${base}/api/${url}`, {
    method,
    headers: { 'X-CSRFToken': csrf, Referer: base, 'Content-Type': 'application/json' },
    data: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok()) throw new Error(`${method} ${url} answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// A card's head: the deepest block holding both its toggle and its mark.
const head = (page, title) =>
  page
    .locator('div')
    .filter({ has: page.getByRole('button', { name: new RegExp(`^(Collapse|Expand) ${escape(title)}$`) }) })
    .filter({ has: page.getByRole('button', { name: /✓ Mark completed|^Undo$/ }) })
    .last();

// Do `act` and wait for the proposal write it makes; returns the write's answer.
async function saved(page, act, marks = false) {
  const path = marks ? /\/proposal\/marks\/$/ : /\/proposal\/$/;
  const answer = page.waitForResponse(
    (response) => path.test(new URL(response.url()).pathname) && ['PATCH', 'POST'].includes(response.request().method()),
  );
  await act();
  const response = await answer;
  if (!response.ok()) throw new Error(`the write answered ${response.status()}: ${await response.text()}`);
  return response.json();
}

export const builder26 = {
  title: 'The Proposal builder on GD1: every deal card saves and marks itself done; Markets checked with no RFP sent',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base } = ctx;
    let dealId;
    let before;
    const markDone = async (title) => {
      const card = head(page, title);
      await saved(page, () => card.getByRole('button', { name: '✓ Mark completed' }).click(), true);
      await card.getByText(/✓ Completed/).waitFor();
    };
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Advisor\'s "Proposal builder" opens on Medical with its deal cards', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'Proposal builder' }).click();
      await page.getByRole('button', { name: /^Medical/ }).click();
      dealId = page.url().match(/\/deals\/(\d+)/)[1];
      before = await api(page, base, `deals/${dealId}/proposal/`);
      const touched = ['output', 'experience', 'summary', 'next_steps', 'markets'].filter((key) => key in before.config);
      if (touched.length || Object.keys(before.marks.stored).length) throw new Error(`GD1 starts with ${touched}`);
      for (const title of ['How the documents look', 'Presentation pages', 'Coverage & marketing intent']) {
        await head(page, title).waitFor();
      }
      for (const title of ['Executive summary', 'Next steps', 'Markets checked']) await head(page, title).waitFor();
    });
    await step('Markets checked lists the carriers that quoted, says no RFP was sent, and waits to show itself', async () => {
      await page.getByText('No RFP email is marked sent yet, so only the carriers that quoted are listed.').waitFor();
      for (const name of ['Aetna', 'Cigna', 'UnitedHealthcare']) {
        await page.getByRole('textbox', { name: `Note for ${name}` }).waitFor();
      }
      await head(page, 'Markets checked').getByText('Not shown').waitFor();
    });
    await step('How the documents look saves "10 columns" and marks itself done', async () => {
      await saved(page, () => page.getByRole('button', { name: '10 columns' }).click());
      await markDone('How the documents look');
    });
    await step('an edit on a completed card takes its own mark off (J19)', async () => {
      const card = head(page, 'How the documents look');
      await card.getByRole('button', { name: 'Expand How the documents look' }).click();
      await saved(page, () => page.getByRole('button', { name: '16 columns' }).click());
      await card.getByRole('button', { name: '✓ Mark completed' }).waitFor();
      await markDone('How the documents look');
    });
    await step('Presentation pages saves a page switch and the plan experience, and its ledger follows', async () => {
      await saved(page, () => page.getByRole('checkbox', { name: 'Your team' }).click());
      await page.getByText('switched off').waitFor();
      const summary = page.getByRole('textbox', { name: 'How the plan has run' });
      await summary.fill('Claims ran at 74% of premium over the last two years.');
      await saved(page, () => summary.blur());
      const ledger = (await api(page, base, `deals/${dealId}/proposal/`)).ledger;
      if (!ledger.find((row) => row.key === 'experience').ready) throw new Error('the experience page still waits');
      await markDone('Presentation pages');
    });
    await step('Coverage & marketing intent marks itself done', async () => {
      await markDone('Coverage & marketing intent');
    });
    await step('the Executive summary saves a picked figure, previews it, and marks itself done', async () => {
      await saved(page, () => page.getByRole('checkbox', { name: /^Lowest quote/ }).click());
      await page.getByText('Medical · Lowest quote').waitFor();
      await head(page, 'Executive summary').getByText('9 figures').waitFor();
      await markDone('Executive summary');
    });
    await step('Next steps saves a step and marks itself done', async () => {
      await page.getByRole('button', { name: '＋ Add a step' }).click();
      const words = page.getByRole('textbox', { name: 'What happens' });
      await words.fill('Decide on the medical plan');
      await saved(page, () => words.blur());
      await head(page, 'Next steps').getByText('1 on the proposal').waitFor();
      await markDone('Next steps');
    });
    await step("Markets checked saves a carrier's note and Show it, and marks itself done", async () => {
      const note = page.getByRole('textbox', { name: 'Note for Cigna' });
      await note.fill('Competitive');
      await saved(page, () => note.blur());
      await saved(page, () => page.getByRole('checkbox', { name: 'Show it' }).last().click());
      await head(page, 'Markets checked').getByText('Shown').waitFor();
      await page.getByRole('button', { name: 'Back to automatic' }).waitFor();
      await markDone('Markets checked');
    });
    await step('the toolbar counts the five marked cards (Presentation pages is optional)', async () => {
      await page.getByText(/✓ 5 of \d+ completed/).waitFor();
    });
    await step('every setting and mark goes back through the same doors, and GD1 reads as before', async () => {
      const defaults = {
        'output.pages.team': true,
        'experience.summary': '',
        'summary.blocks': [],
        next_steps: [],
        'markets.lines.medical.notes.cigna': '',
        'markets.on': null,
      };
      await api(page, base, `deals/${dealId}/proposal/`, 'PATCH', defaults);
      for (const card of ['output', 'pages', 'coverage', 'summary', 'next_steps', 'markets']) {
        const line = card === 'markets' ? 'medical' : '';
        await api(page, base, `deals/${dealId}/proposal/marks/`, 'POST', { card, line, done: false });
      }
      const after = await api(page, base, `deals/${dealId}/proposal/`);
      const same = JSON.stringify([after.config, after.marks.stored]) === JSON.stringify([before.config, before.marks.stored]);
      if (!same) throw new Error(`GD1 reads ${JSON.stringify({ config: after.config, marks: after.marks.stored })}`);
    });
  },
};
