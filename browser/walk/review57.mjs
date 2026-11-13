// Slice 57's "done when" (plan.md §13.10 row 57; L30, L36, L38, L39, L42, L64): the Ask card changes an open link. Run
// it with `--need s57`. It writes to GD6 (a request with its link, a draft, the change, a reminder), so seed GD6 again
// afterwards (`seed_golden GD6`).
//
// Staff: GD6 has a link out to Jordan (synthetic) asking DBA and Website (made and marked sent by the API, as "A new
// link…" and Copy link would). On the request page a click on Jordan in the who bar puts the Ask card on their link:
// DBA and Website read "On their link" and their form fills the middle. Years in Business is ticked (a draft named
// for the request: "Will be added"), DBA unticked ("Coming off"); on the Census tab the census is switched on, which
// needs a PIN: the card says so and Update link waits until PIN required is picked; Update link answers the PIN once.
// Then the settings card (Edit) takes a reminder to nudge them, which waits for Update link too. Done when: the
// request asks Years in Business and Website, not DBA, and the census gaps; its link asks for a PIN; the client (no
// session) needs the PIN, and with it sees Years in Business and Website and not DBA; the reminder is on the link.

const WHO = 'Jordan Example (synthetic)';

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

function keysOf(payload) {
  return (payload.intake?.sections || []).flatMap((section) => section.fields.map((entry) => entry.key));
}

// The Update link POST itself (not its dry run): a step waits for its answer, never for words a toast already shows.
const updated = (page) =>
  page.waitForResponse((r) => r.request().method() === 'POST' && /\/form\/$/.test(new URL(r.url()).pathname) && !r.url().includes('dry_run'));

function dayIn(days) {
  const when = new Date();
  when.setDate(when.getDate() + days);
  const pad = (n) => String(n).padStart(2, '0');
  return `${when.getFullYear()}-${pad(when.getMonth() + 1)}-${pad(when.getDate())}`;
}

export const review57 = {
  title: 'Slice 57: the Ask card changes an open link',
  deal: 'GD6',
  async run(ctx, { signIn }) {
    const { page, step, base, spec } = ctx;
    const shot = (name) => process.env.WALK_SHOTS && page.screenshot({ path: `${process.env.WALK_SHOTS}/${name}.png` });
    let dealId;
    let made;
    let pin;
    await signIn(ctx);
    await step('staff: GD6 found, its tray empty; a link to Jordan asking DBA and Website is out', async () => {
      const found = await api(page, base, `clients/?q=${encodeURIComponent(spec.client)}`);
      dealId = found.results.find((row) => row.name === spec.client)?.deal?.id;
      if (!dealId) throw new Error(`no deal for ${spec.client}`);
      const tray = await api(page, base, `deals/${dealId}/review/tray/`);
      if (tray.count) throw new Error(`the tray already holds ${tray.count}: seed GD6 again`);
      const asks = { intake: { scope: 'selected', keys: ['dba', 'website'] } };
      made = (await api(page, base, `deals/${dealId}/review/requests/`, 'POST', { people: [{ name: WHO }], asks })).links[0];
      await api(page, base, `links/${made.link_id}/`, 'PATCH', { action: 'mark_sent', copied: true });
    });
    await step('the request page: a click on Jordan puts the Ask card on their link, and their form fills the middle', async () => {
      await page.goto(`${base}/deals/${dealId}/review?view=request`);
      await page.getByRole('button', { name: WHO }).first().click();
      await page.waitForURL(/target=link%3A\d+|target=link:\d+/);
      const rail = page.getByLabel('What to ask');
      await rail.getByText('On their link').first().waitFor();
      await page.getByLabel('Their form').getByText('Website').first().waitFor();
      await shot('s57-ask-card');
    });
    await step('a tick drafts Years in Business for their link; an untick takes DBA off', async () => {
      const rail = page.getByLabel('What to ask');
      await rail.getByRole('checkbox', { name: 'Ask for Years in Business' }).click();
      await rail.getByText('Will be added').waitFor();
      await rail.getByRole('checkbox', { name: 'Take DBA off' }).click();
      await rail.getByText('Coming off').waitFor();
    });
    await step('the Census tab: switching the census on needs a PIN, and Update link waits', async () => {
      await page.getByRole('button', { name: /^Census/, pressed: false }).click();
      await page.getByLabel('Census', { exact: true }).selectOption('missing');
      await page.getByText(/Census needs at least a PIN/).first().waitFor();
      const update = page.getByRole('button', { name: 'Update link' }).last();
      if (await update.isEnabled()) throw new Error('Update link is open while a PIN is owed');
    });
    await step('PIN required is picked; Update link changes their link and shows the PIN once', async () => {
      await page.getByRole('radio', { name: /PIN required/ }).last().check();
      const update = page.getByRole('button', { name: 'Update link' }).last();
      await page.waitForFunction(() => {
        const buttons = [...document.querySelectorAll('button')].filter((b) => b.textContent === 'Update link');
        return buttons.length && !buttons[buttons.length - 1].disabled;
      });
      const answered = updated(page);
      await update.click();
      if (!(await answered).ok()) throw new Error('Update link was refused');
      await page.getByText('Their link is updated', { exact: false }).first().waitFor();
      const digits = await page.getByLabel(/^PIN \d{6}$/).first().getAttribute('aria-label');
      pin = digits.replace('PIN ', '');
      await shot('s57-updated');
    });
    await step('the settings card: a reminder to nudge them waits for Update link, then goes on the link', async () => {
      await page.getByRole('button', { name: 'Done' }).last().click();
      await page.getByRole('button', { name: 'Edit', exact: true }).first().click();
      const card = page.getByLabel('Edit link settings');
      await card.getByLabel(`The day to remind you to nudge ${WHO}`).fill(dayIn(1));
      const answered = updated(page);
      await card.getByRole('button', { name: 'Update link' }).click();
      if (!(await answered).ok()) throw new Error('Update link was refused');
      await shot('s57-settings');
    });
    await step('done when: the request asks Years in Business and Website, not DBA, and the census gaps, behind a PIN', async () => {
      const { requests } = await api(page, base, `deals/${dealId}/review/requests/`);
      const row = requests.find((request) => request.recipients.some((person) => person.link_id === made.link_id));
      const person = row.recipients.find((entry) => entry.link_id === made.link_id);
      if (!row.asks.includes('The census gaps')) throw new Error(`asks: ${row.asks.join(' · ')}`);
      if (person.security !== 'pin' || person.nudge_on !== dayIn(1)) throw new Error(`link: ${person.security} ${person.nudge_on}`);
    });
    await step('the client (no session) needs the PIN, then sees Years in Business and Website and not DBA', async () => {
      const context = await page.context().browser().newContext();
      const token = made.path.split('/').pop();
      const portal = (door) => `${base}/api/portal/${token}/${door}`;
      const locked = await context.request.get(portal(''));
      if (locked.status() !== 428) throw new Error(`the page answered ${locked.status()} without the PIN`);
      const verified = await context.request.post(portal('verify/'), { data: { pin } });
      if (!verified.ok()) throw new Error(`the PIN answered ${verified.status()}`);
      const header = verified.headers()['x-link-verification'];
      const payload = await (await context.request.get(portal(''), { headers: { 'X-Link-Verification': header } })).json();
      const keys = keysOf(payload);
      if (!keys.includes('years_in_business') || !keys.includes('website') || keys.includes('dba')) throw new Error(`asked: ${keys}`);
      await context.close();
    });
  },
};
