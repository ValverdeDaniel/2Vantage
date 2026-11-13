// The catch-up after slices 57–58 (I35–I39, I15, I46; M50, M54): a reminder to nudge someone, set in their link's
// settings card, is a row on the deal's Agenda whose Later and ✓ go through review's set_nudge and finish_nudge; Card 1
// asks for a chosen fillable form itself, to fill online. Run it with `--need catchup` on a fresh GD3 (`manage.py
// seed_golden GD3`, which picks Florida Blue 51+ by group size). It writes to GD3 (a request with its link and
// reminder, a deal note, a tray draft): seed GD3 again afterwards.
//
// Staff: a link to Jordan (synthetic) asking their census file is out, and the settings card's reminder (slice 57's
// write, walked by s57) is set two days out. On the Agenda the row "Nudge Jordan … about their form" waits in Up next
// with Later and ✓, and Open ▸ opens the link's settings card. Later offers only the picks before the day the link
// runs out (Next week is past it), moves the reminder (review's own read says the new day) and keeps the note as a
// deal note; ✓ stamps it done and it stays in Done. On the Overview, the medical questionnaire's "＋ Ask" puts the
// form in the request tray (`qform:fl_blue_51`), not its file.

const WHO = 'Jordan Example (synthetic)';
const NUDGE = `Nudge ${WHO} about their form`;
const NOTE = 'Out of office until Thursday (catch-up walk, synthetic)';

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

/** The ISO day `days` after the agency's `today` (the Agenda payload's), counted on the calendar. */
function dayAfter(today, days) {
  return new Date(Date.parse(`${today}T00:00:00Z`) + days * 86400000).toISOString().slice(0, 10);
}

const section = (page, title) => page.locator('.bnf-ag-block', { has: page.getByRole('button', { name: new RegExp(`^[▾▸] ${title}`) }) });
const overview = (page) => page.getByRole('region', { name: 'Overview' });

export const catchup = {
  title: 'Catch-up after slices 57–58: Later and ✓ on a nudge row go through review; Card 1 asks for the form online',
  deal: 'GD3',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, base } = ctx;
    let dealId;
    let linkId;
    let today;
    const reminder = async () => {
      const { requests } = await api(page, base, `deals/${dealId}/review/requests/`);
      return requests.flatMap((request) => request.recipients).find((person) => person.link_id === linkId);
    };
    await signIn(ctx);
    await openDeal(ctx);

    await step('staff: a link to Jordan asking their census file is out, with a reminder to nudge them in 2 days', async () => {
      dealId = Number(page.url().match(/\/deals\/(\d+)/)[1]);
      ({ today } = await api(page, base, `deals/${dealId}/agenda/`));
      const { requests } = await api(page, base, `deals/${dealId}/review/requests/`);
      if (requests.length) throw new Error('GD3 already has a request: run manage.py seed_golden GD3 first');
      const asks = { census: { file: true } };
      linkId = (await api(page, base, `deals/${dealId}/review/requests/`, 'POST', { people: [{ name: WHO }], asks })).links[0].link_id;
      await api(page, base, `links/${linkId}/`, 'PATCH', { action: 'mark_sent', copied: true });
      await api(page, base, `links/${linkId}/`, 'PATCH', { action: 'nudge', day: dayAfter(today, 2) });
      if ((await reminder()).nudge_on !== dayAfter(today, 2)) throw new Error('the link holds no reminder');
    });

    await step('the Agenda: the nudge row waits in Up next with its day, Later and ✓; Open ▸ goes to the link’s settings (I35)', async () => {
      await page.goto(`${base}/deals/${dealId}/agenda`);
      const row = section(page, 'Up next').locator('.bnf-ag-item', { hasText: NUDGE });
      await row.waitFor();
      await row.getByText('Nudge', { exact: true }).waitFor();
      await row.getByRole('button', { name: 'Later' }).waitFor();
      await row.getByRole('button', { name: 'Mark this task done' }).waitFor();
      const open = await row.getByRole('link', { name: 'Open ▸' }).getAttribute('href');
      const want = `/deals/${dealId}/review?view=request&target=link%3A${linkId}&settings=${linkId}`;
      if (open !== want) throw new Error(`Open ▸ goes to ${open}`);
    });

    await step('Open ▸ opens the request page with that link’s settings card and its reminder day', async () => {
      await page.locator('.bnf-ag-item', { hasText: NUDGE }).getByRole('link', { name: 'Open ▸' }).click();
      await page.waitForURL(/view=request/);
      await page.getByText('Remind me to nudge', { exact: true }).waitFor();
      const value = await page.getByLabel(/^The day to remind you to nudge/).inputValue();
      if (value !== dayAfter(today, 2)) throw new Error(`the settings card reads ${value}`);
    });

    await step('Later: only the picks before the day the link runs out; In 3 days moves the reminder through review (I15, I37)', async () => {
      await page.goto(`${base}/deals/${dealId}/agenda`);
      const row = page.locator('.bnf-ag-item', { hasText: NUDGE });
      await row.getByRole('button', { name: 'Later' }).click();
      await row.getByRole('button', { name: 'In 3 days' }).waitFor();
      if (await row.getByRole('button', { name: 'Next week' }).count()) throw new Error('Next week is offered past the link’s last day');
      await row.getByRole('button', { name: 'In 3 days' }).click();
      await row.getByLabel('Why it waits').fill(NOTE);
      await row.locator('form').getByRole('button', { name: 'Later' }).click();
      await page.getByText('Task moved').waitFor();
      const moved = await reminder();
      if (moved.nudge_on !== dayAfter(today, 3)) throw new Error(`review holds ${moved.nudge_on}`);
      const notes = await api(page, base, `deals/${dealId}/notes/`);
      if (!JSON.stringify(notes).includes(NOTE)) throw new Error('the note is not on the deal');
      await section(page, 'Up next').locator('.bnf-ag-item', { hasText: NUDGE }).waitFor();
    });

    await step('✓ stamps the reminder done through review, and the row stays in Done (I37, I39)', async () => {
      await page.locator('.bnf-ag-item', { hasText: NUDGE }).getByRole('button', { name: 'Mark this task done' }).click();
      await page.getByText('Task done').waitFor();
      if (!(await reminder()).nudge_done_at) throw new Error('review holds no done stamp');
      await page.getByRole('button', { name: /^▸ Done/ }).click();
      const done = section(page, 'Done').locator('.bnf-ag-item', { hasText: NUDGE });
      await done.waitFor();
      if (await done.getByRole('button').count()) throw new Error('a done nudge still offers a button');
    });

    await step('Card 1: the medical questionnaire’s ＋ Ask puts the form itself in the tray, to fill online (M54)', async () => {
      await page.goto(`${base}/deals/${dealId}/overview`);
      const form = overview(page).getByRole('region', { name: 'Medical questionnaire' });
      const ask = form.getByRole('button', { name: '＋ Ask' });
      await ask.waitFor();
      const title = await ask.getAttribute('title');
      if (!/fill it out online on their link/.test(title || '')) throw new Error(`＋ Ask says "${title}"`);
      await ask.click();
      await form.getByText('✓ In tray').waitFor();
      const tray = await api(page, base, `deals/${dealId}/review/tray/`);
      if (!tray.items.some((entry) => entry.ref === 'qform:fl_blue_51')) throw new Error('the tray holds no qform:fl_blue_51');
    });
  },
};
