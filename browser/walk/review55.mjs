// Slice 55's "done when" (plan.md §13.10 row 55; L9, L11, L14–L17, L43; B38, C34; OQ84, OQ85): an approved answer is
// stored with origin `client`. Run it with `--need s55`. It writes to GD6 (a request, the client's answers, two of them
// approved), so seed GD6 again afterwards (`seed_golden GD6`).
//
// Staff (signed in, through the API the Review tab uses): a request on GD6 asking its whole intake, copied. Client
// (a fresh context with no session, through the portal's own API): two changed answers saved, then Submit. Staff, in
// Chrome: the Intake tab's section bar says what came back with "Approve N ready ✓"; Review ▸ opens the queue at
// Intake; A approves the first answer; the section bar's "Approve 1 ready ✓" takes the other; the Board's To review
// lane is empty again; the intake API holds both answers with origin `client`, the link and the approver.

const CHANGED = {
  payroll_vendor: 'Example Payroll Two (synthetic)',
  dba: 'Golden G2M Trucking (synthetic)',
};

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

function baseOf(payload, key) {
  for (const section of payload.intake?.sections || []) {
    const found = (section.fields || []).find((field) => field.key === key);
    if (found) return found.base;
  }
  throw new Error(`the portal page does not ask ${key}`);
}

export const review55 = {
  title: 'Slice 55: an approved answer is stored with origin client',
  deal: 'GD6',
  async run(ctx, { signIn }) {
    const { page, step, base, spec } = ctx;
    let dealId;
    let made;
    await signIn(ctx);
    await step('staff: GD6 gets a request for its whole intake, copied (marked sent)', async () => {
      const found = await api(page, base, `clients/?q=${encodeURIComponent(spec.client)}`);
      dealId = found.results.find((row) => row.name === spec.client)?.deal?.id;
      if (!dealId) throw new Error(`no deal for ${spec.client}`);
      made = await api(page, base, `deals/${dealId}/review/requests/`, 'POST', {
        people: [{ name: 'Riley Example (synthetic)' }],
        asks: { intake: { scope: 'all' } },
      });
      await api(page, base, `links/${made.links[0].link_id}/`, 'PATCH', { action: 'mark_sent', copied: true });
    });
    await step('client, with no session: two answers changed on the portal, then Submit', async () => {
      const context = await page.context().browser().newContext();
      const token = made.links[0].path.split('/').pop();
      const portal = (door) => `${base}/api/portal/${token}/${door}`;
      const payload = await (await context.request.get(portal(''))).json();
      const answers = Object.fromEntries(
        Object.entries(CHANGED).map(([key, value]) => [`intake:${key}`, { value, base: baseOf(payload, key) }]),
      );
      const saved = await context.request.post(portal('save/'), { data: { answers } });
      if (!saved.ok()) throw new Error(`the save answered ${saved.status()}: ${await saved.text()}`);
      const sent = await context.request.post(portal('submit/'), { data: { answers: {} } });
      if (!sent.ok()) throw new Error(`the submit answered ${sent.status()}: ${await sent.text()}`);
      await context.close();
      const intake = await api(page, base, `deals/${dealId}/intake/`);
      if (intake.answers.payroll_vendor === CHANGED.payroll_vendor) throw new Error('a pending answer landed (OQ85)');
    });
    await step('the Intake tab’s section bar: "↩ Riley … answered 2 · 2 ready" and "Approve 2 ready ✓"', async () => {
      await page.goto(`${base}/deals/${dealId}/intake`);
      const bar = page.getByLabel('Intake: review and requests');
      await bar.getByText('↩ Riley Example (synthetic) answered 2 · 2 ready').waitFor();
      await bar.getByRole('button', { name: 'Approve 2 ready ✓' }).waitFor();
      await bar.getByRole('button', { name: /2 to review/ }).waitFor();
    });
    await step('Review ▸ opens the review queue at Intake: From the client, the first answer open', async () => {
      await page.getByLabel('Intake: review and requests').getByRole('button', { name: 'Review ▸' }).click();
      await page.waitForURL(/\/review\?view=queue&section=intake/);
      await page.getByRole('button', { name: /^Intake/, pressed: true }).waitFor();
      await page.getByText('From the client', { exact: true }).waitFor();
      await page.getByText('0 of 2 reviewed').waitFor();
      await page.getByText(CHANGED.dba, { exact: true }).first().waitFor();
      if (process.env.WALK_SHOTS) await page.screenshot({ path: `${process.env.WALK_SHOTS}/s55-queue.png` });
    });
    await step('A approves it and moves on; opened again, the row reads Approved with ↶ Undo', async () => {
      await page.keyboard.press('a');
      await page.getByText('1 of 2 reviewed').waitFor();
      await page.getByText('DBA', { exact: true }).click();
      await page.getByText('Approved', { exact: true }).waitFor();
      await page.getByRole('button', { name: '↶ Undo' }).waitFor();
      if (process.env.WALK_SHOTS) await page.screenshot({ path: `${process.env.WALK_SHOTS}/s55-approved.png` });
    });
    await step('back on Intake: "Approve 1 ready ✓" takes the other answer', async () => {
      await page.goto(`${base}/deals/${dealId}/intake`);
      const bar = page.getByLabel('Intake: review and requests');
      await bar.getByRole('button', { name: 'Approve 1 ready ✓' }).click();
      await page.getByText('1 answer from the client approved').waitFor();
      await bar.getByRole('button', { name: /0 to review/ }).waitFor();
    });
    await step('the Board’s To review lane is empty again', async () => {
      await page.goto(`${base}/deals/${dealId}/review`);
      await page.getByRole('region', { name: 'To review' }).getByText('Nothing came back to review.').waitFor();
    });
    await step('done when: both answers are stored with origin client, the link and the approver', async () => {
      const intake = await api(page, base, `deals/${dealId}/intake/`);
      for (const [key, value] of Object.entries(CHANGED)) {
        const source = intake.sources[key] || {};
        if (intake.answers[key] !== value) throw new Error(`${key} reads "${intake.answers[key]}"`);
        if (source.origin !== 'client' || source.link !== made.links[0].link_id || !source.by) {
          throw new Error(`${key}'s source is ${JSON.stringify(source)}`);
        }
      }
    });
  },
};
