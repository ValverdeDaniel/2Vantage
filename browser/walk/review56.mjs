// Slice 56's "done when" (plan.md §13.10 row 56; L22, L29, L37, L49–L54; B12, B27; OQ87): asks gathered in the tray go
// out on one link. Run it with `--need s56`. It writes to GD6 (an answer blanked, asks, a new request, a client
// question and our reply), so seed GD6 again afterwards (`seed_golden GD6`).
//
// Staff, in Chrome: GD6's Website answer is blanked (API) so the Intake row offers "＋ Ask" (B12); the checklist's
// Renewal row's "＋ Ask" (B27); both wait in the tray, whose bar on every tab names where they go; the snippet opens the
// request page, where the Census tab's "Their census file" is ticked and DBA (on file) is sent back with a note from
// its card. Going out says no open link can take them: "Choose who ▸", a typed person, "Send on a new link ▸": one link.
// Then the client (no session) sees all four on that one link, with the send-back as a follow-up that needs their
// answer, and asks a question; the Board lists it, Answer ▸ opens the request page, and our reply closes it.

const ASKED = ['intake:website', 'doc:renewal', 'census:file', 'intake:dba'];
const NOTE = 'Is this still the name you trade under? (synthetic)';

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

function field(payload, key) {
  for (const section of payload.intake?.sections || []) {
    const found = (section.fields || []).find((entry) => entry.key === key);
    if (found) return found;
  }
  return null;
}

export const review56 = {
  title: 'Slice 56: asks gathered in the tray go out on one link',
  deal: 'GD6',
  async run(ctx, { signIn }) {
    const { page, step, base, spec } = ctx;
    const shot = (name) => process.env.WALK_SHOTS && page.screenshot({ path: `${process.env.WALK_SHOTS}/${name}.png` });
    let dealId;
    let link;
    let token;
    await signIn(ctx);
    await step('staff: GD6 found, its tray empty, its Website answer blanked so the row can be asked', async () => {
      const found = await api(page, base, `clients/?q=${encodeURIComponent(spec.client)}`);
      dealId = found.results.find((row) => row.name === spec.client)?.deal?.id;
      if (!dealId) throw new Error(`no deal for ${spec.client}`);
      const tray = await api(page, base, `deals/${dealId}/review/tray/`);
      if (tray.count) throw new Error(`the tray already holds ${tray.count}: seed GD6 again`);
      await api(page, base, `deals/${dealId}/intake/`, 'PATCH', { answers: { website: '' } });
    });
    await step('Intake: the blank Website row says "＋ Ask"; a click puts it in the tray (B12)', async () => {
      await page.goto(`${base}/deals/${dealId}/intake`);
      const row = page.locator('[data-intake-field="website"]');
      await row.getByRole('button', { name: '＋ Ask' }).click();
      await row.getByText('✓ In tray').waitFor();
    });
    await step('the checklist’s Renewal row asks for the file too (B27); the bar says "Request tray · 2 · → needs a new link"', async () => {
      const renewal = page.getByRole('group', { name: /renewal/i }).first();
      await renewal.getByRole('button', { name: '＋ Ask' }).click();
      await renewal.getByText('✓ In tray').waitFor();
      const bar = page.getByRole('region', { name: 'Request tray' });
      await bar.getByText(/Request tray · 2/).waitFor();
      await bar.getByText('→ needs a new link').waitFor();
      await shot('s56-tray-bar');
    });
    await step('Review & send ▸ opens the snippet by section; Open the request ▸ goes to the request page', async () => {
      await page.getByRole('button', { name: 'Review & send ▸' }).click();
      const snippet = page.getByRole('dialog', { name: 'The request tray' });
      await snippet.getByText('Intake · 1').waitFor();
      await snippet.getByText('Documents · 1').waitFor();
      await snippet.getByRole('button', { name: 'Open the request ▸' }).click();
      await page.waitForURL(/\/review\?view=request/);
      await page.getByRole('region', { name: 'Request tray' }).waitFor({ state: 'detached' });
    });
    await step('the request page’s Census tab: ticking "Their census file" adds it', async () => {
      await page.getByRole('button', { name: /^Census/, pressed: false }).click();
      await page.getByRole('checkbox', { name: 'Ask for Their census file' }).click();
      await page.getByText('3 in the request tray').waitFor();
    });
    await step('Intake tab: DBA (on file) goes back with a note from its card', async () => {
      await page.getByRole('button', { name: /^Intake( ·|$)/, pressed: false }).click();
      await page.getByRole('button', { name: 'DBA', exact: true }).click();
      const card = page.getByLabel('DBA: its thread');
      await card.getByRole('button', { name: 'To client' }).click();
      await card.getByLabel('Note').fill(NOTE);
      await card.getByRole('button', { name: 'Send back' }).click();
      await page.getByText('4 in the request tray').waitFor();
      await shot('s56-request-page');
    });
    await step('Going out: no open link can take them; Choose who ▸, a typed person, Send on a new link ▸', async () => {
      const going = page.getByLabel('Going out');
      await going.getByText('Needs a new link').waitFor();
      await going.getByRole('button', { name: 'Choose who ▸' }).click();
      const who = page.getByRole('group', { name: 'Choose who to ask' });
      await who.getByLabel('Their name').fill('Riley Example (synthetic)');
      await who.getByRole('button', { name: 'Add' }).click();
      await who.getByRole('button', { name: 'Send on a new link ▸' }).click();
      await page.getByText('Link ready: paste each into your own email.', { exact: false }).waitFor();
      await going.getByText('The request tray is empty').waitFor();
      await shot('s56-sent');
    });
    await step('done when: one new request carries all four, on one link, and the tray is empty', async () => {
      const board = await api(page, base, `deals/${dealId}/review/board/`);
      const requests = board.lanes.waiting.filter((row) => row.recipients.some((p) => p.name === 'Riley Example (synthetic)'));
      if (requests.length !== 1 || requests[0].recipients.length !== 1) throw new Error(`requests: ${JSON.stringify(requests)}`);
      link = requests[0].recipients[0];
      token = link.path.split('/').pop();
      const tray = await api(page, base, `deals/${dealId}/review/tray/`);
      if (tray.count) throw new Error(`the tray still holds ${tray.count}`);
      for (const ref of ASKED) if (!tray.out[ref]) throw new Error(`${ref} is not out with the client`);
    });
    await step('the client, with no session, sees all four on that link and the send-back needing their answer', async () => {
      const context = await page.context().browser().newContext();
      const portal = (door) => `${base}/api/portal/${token}/${door}`;
      const payload = await (await context.request.get(portal(''))).json();
      if (!field(payload, 'website') || field(payload, 'dba')?.locked !== false) throw new Error('Website or DBA is not asked');
      if (!payload.documents.some((slot) => slot.slot === 'renewal') || !payload.census_file) throw new Error('files not asked');
      const card = payload.follow_ups.find((entry) => entry.ref === 'intake:dba');
      if (!card?.needs_answer || card.thread[0].text !== NOTE) throw new Error(`follow-ups: ${JSON.stringify(payload.follow_ups)}`);
      const asked = await context.request.post(portal('questions/'), {
        data: { questions: [{ ref: 'doc:renewal', text: 'Which year’s renewal do you need? (synthetic)' }] },
      });
      if (asked.status() !== 201) throw new Error(`the question answered ${asked.status()}`);
      await context.close();
    });
    await step('the Board lists their question; Answer ▸ opens the request page, where our reply closes it', async () => {
      await page.goto(`${base}/deals/${dealId}/review`);
      await page.getByText('1 question from the client').waitFor();
      await page.getByRole('button', { name: 'Answer ▸' }).click();
      await page.waitForURL(/view=request&pane=documents/);
      await page.getByRole('button', { name: /renewal/i }).first().click();
      const card = page.getByLabel(/: its thread$/);
      await card.getByText('Which year’s renewal do you need? (synthetic)').waitFor();
      await card.getByLabel('Note').fill('The current one, please.');
      await card.getByRole('button', { name: 'Reply' }).click();
      await card.getByText(/answered/).waitFor();
      await shot('s56-replied');
    });
    await step('the client answers DBA again and submits; it is back in the queue with its thread', async () => {
      const context = await page.context().browser().newContext();
      const portal = (door) => `${base}/api/portal/${token}/${door}`;
      const payload = await (await context.request.get(portal(''))).json();
      const answers = { 'intake:dba': { value: 'Golden G2M Freight (synthetic)', base: field(payload, 'dba').base } };
      const saved = await context.request.post(portal('submit/'), { data: { answers } });
      if (!saved.ok()) throw new Error(`the submit answered ${saved.status()}: ${await saved.text()}`);
      await context.close();
      await page.goto(`${base}/deals/${dealId}/review?view=queue&section=intake`);
      await page.getByText('Golden G2M Freight (synthetic)').first().waitFor();
      await page.getByText(NOTE).waitFor();
    });
    await step('the queue: N writes a team note; X sends it back with a note: Going back, and the tray names Riley’s link', async () => {
      await page.keyboard.press('n');
      await page.getByLabel('Team note').fill('Check with Stephanie first (synthetic).');
      await page.keyboard.press('Enter');
      await page.getByText('Check with Stephanie first (synthetic).').waitFor();
      await page.getByLabel('Team note').waitFor({ state: 'detached' }); // the note box closes, the item stays open
      await page.keyboard.press('x');
      await page.getByLabel('Back to the client, with a note').fill('Please give the legal trade name. (synthetic)');
      await page.keyboard.press('Enter');
      await page.getByText('1 of 1 reviewed').waitFor();
      await page.getByRole('button', { name: /Going back/ }).getByText('1').waitFor();
      await page.getByRole('region', { name: 'Request tray' }).getByText(/→ Riley’s link/).waitFor(); // its own link
      await shot('s56-queue');
    });
  },
};
