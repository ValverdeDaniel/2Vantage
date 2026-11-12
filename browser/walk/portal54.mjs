// Slice 54's "done when" (plan.md §13.10 row 54; L76–L98, L136; B43, C35; OQ80, OQ84): a client fills answers and
// uploads files on a phone-sized screen. Run it with `--need s54`. It writes to GD6 (two intake answers cleared, a
// request, the client's answers, files, a person and the BOR), so seed GD6 again afterwards (`seed_golden GD6`).
//
// Staff side (signed in, through the API the Review tab uses): clear two of GD6's answers, then a request that asks
// the intake's blanks, contacts and the BOR, the census (its required gaps, so people can be added) with the census
// file, and the medical invoice; copy it. Client side, a fresh browser at 390×844 with no session: the PIN screen, the
// page (top bar, to-do list), typing two answers (autosave), adding a contact and an employee with their details,
// attaching the census file and the invoice, signing the BOR, Save progress, Submit, the thank-you; then the Board
// shows it answered and the old /b/ link says it has moved. Nothing on the page may be wider than the phone.

const PHONE = { width: 390, height: 844 };
const CLEARED = { payroll_vendor: '', website: '' };
const CSV = 'First Name,Last Name,DOB,Gender,Zip\r\nRowan,Newhire,03/04/1990,F,33602\r\n';
const PDF = '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n';

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

const fitsThePhone = async (phone) => {
  const wide = await phone.evaluate(() => document.documentElement.scrollWidth);
  if (wide > 391) throw new Error(`the page is ${wide}px wide on a 390px screen`);
};

export const portal54 = {
  title: 'Slice 54: a client fills answers and uploads files on a phone-sized screen',
  deal: 'GD6',
  async run(ctx, { signIn }) {
    const { page, step, base, spec } = ctx;
    let made;
    let phone;
    let dealId;
    await signIn(ctx);
    await step('staff: GD6 gets a request for its blanks, contacts, the BOR, the census and the medical invoice', async () => {
      const found = await api(page, base, `clients/?q=${encodeURIComponent(spec.client)}`);
      dealId = found.results.find((row) => row.name === spec.client)?.deal?.id;
      if (!dealId) throw new Error(`no deal for ${spec.client}`);
      await api(page, base, `deals/${dealId}/intake/`, 'PATCH', { answers: CLEARED });
      made = await api(page, base, `deals/${dealId}/review/requests/`, 'POST', {
        people: [{ name: 'Riley Example (synthetic)' }],
        asks: {
          intake: { scope: 'missing', blocks: ['contacts', 'bor'] },
          census: { scope: 'missing', file: true },
          documents: { slots: ['invoice@medical'] },
        },
        message: 'A few things before we go to market — thank you!',
      });
      const link = made.links[0];
      if (link.security !== 'pin' || !/^\d{6}$/.test(link.pin)) throw new Error('the census ask did not raise a PIN');
      await api(page, base, `links/${link.link_id}/`, 'PATCH', { action: 'mark_sent', copied: true });
    });
    await step('client, on a phone with no session: the link asks for the PIN first', async () => {
      const context = await page.context().browser().newContext({ viewport: PHONE, isMobile: true, hasTouch: true, locale: 'en-US' });
      phone = await context.newPage();
      phone.setDefaultTimeout(15000);
      await phone.goto(`${base}${made.links[0].path}`);
      await phone.getByRole('heading', { name: 'This link is protected' }).waitFor();
      await phone.getByLabel('Your 6-digit PIN').fill(made.links[0].pin);
      await phone.getByRole('button', { name: 'Open', exact: true }).click();
    });
    await step('the page: "Secure link · expires in 7 days", the to-do list, the broker’s note, nothing wider than the phone', async () => {
      await phone.getByText(/^Secure link · expires in [67] days$/).waitFor();
      await phone.getByText('Your to-do list').waitFor();
      await phone.getByText('A few things before we go to market — thank you!').waitFor();
      await fitsThePhone(phone);
    });
    await step('two intake answers typed, saved automatically', async () => {
      await phone.getByLabel('Payroll Vendor').fill('Example Payroll Co. (synthetic)');
      await phone.getByLabel('Website').fill('https://example.com/synthetic');
      await phone.getByText(/Saved automatically at .+ — you can come back to this link any time\.$/).waitFor({ timeout: 20000 });
    });
    await step('a contact added in the Contacts card', async () => {
      await phone.getByRole('button', { name: '＋ Add contact' }).click();
      const names = phone.getByLabel('Name', { exact: true });
      await names.last().fill('Jordan Example (synthetic)');
      await phone.getByLabel('Email', { exact: true }).last().fill('jordan@example.test');
    });
    await step('＋ Add an employee: Rowan Newhire appears with what we ask of them', async () => {
      await phone.getByRole('button', { name: '＋ Add an employee' }).click();
      await phone.getByLabel('First name').fill('Rowan');
      await phone.getByLabel('Last name').fill('Newhire');
      await phone.getByRole('button', { name: 'Add', exact: true }).click();
      await phone.getByText('Rowan Newhire', { exact: true }).waitFor();
      await phone.getByLabel('Date of Birth').fill('03/04/1990');
      await fitsThePhone(phone);
    });
    await step('the census file and the medical invoice attached: "attached — save to send"', async () => {
      await phone.getByLabel('Upload Attach your census file').setInputFiles({ name: 'Rowan census (synthetic).csv', mimeType: 'text/csv', buffer: Buffer.from(CSV) });
      await phone.getByLabel(/^Upload Current invoice/).setInputFiles({ name: 'invoice (synthetic).pdf', mimeType: 'application/pdf', buffer: Buffer.from(PDF) });
      if ((await phone.getByText('attached — save to send').count()) < 2) throw new Error('the to-do list does not say both are attached');
    });
    await step('the BOR signed by typing a name; Save progress sends the files and the signature', async () => {
      await phone.getByLabel('Sign the Broker of Record (type your full name)').fill('Jordan Example');
      await phone.getByRole('button', { name: 'Save progress' }).click();
      await phone.getByText(/Progress saved at .+ — you can come back to this link any time\.$/).waitFor({ timeout: 20000 });
      await phone.getByText('BOR signed by Jordan Example').waitFor();
      await phone.getByText(/^Received — Rowan census \(synthetic\)\.csv$/).waitFor();
      await phone.getByText(/^Received — invoice \(synthetic\)\.pdf$/).waitFor();
      await fitsThePhone(phone);
      if (process.env.WALK_SHOTS) await phone.screenshot({ path: `${process.env.WALK_SHOTS}/s54-phone-saved.png` });
    });
    await step('Submit: it says what is still open, then "Thank you — sent to Vantage"', async () => {
      const submit = phone.getByRole('button', { name: /^Submit to .+ ▸$/ });
      await submit.click();
      const again = phone.getByRole('button', { name: /still open — submit anyway\?$/ });
      if (await again.count()) await again.click();
      await phone.getByText(/^Thank you — sent to /).waitFor();
    });
    await step('staff: the Board shows the request answered; the files came in as the client’s', async () => {
      const board = await api(page, base, `deals/${dealId}/review/board/`);
      const request = [...(board.lanes?.waiting || [])].find((row) => row.id === made.request.id);
      if (request) throw new Error('the answered request is still waiting on the client');
      const docs = await api(page, base, `deals/${dealId}/documents/`);
      const theirs = docs.filter((doc) => doc.source === 'client');
      if (theirs.length < 2) throw new Error(`expected the two client files, found ${theirs.length}`);
    });
    await step('staff: View as client shows the page read-only under the Preview banner', async () => {
      await page.goto(`${base}/preview/links/${made.links[0].link_id}`);
      await page.getByText('— this is what the client sees. Nothing you type here is saved.').waitFor();
      await page.getByText('Rowan Newhire', { exact: true }).waitFor();
      if (!(await page.getByLabel('Payroll Vendor').isDisabled())) throw new Error('the preview takes typing');
      if (await page.getByRole('button', { name: 'Save progress' }).count()) throw new Error('the preview offers Save');
    });
    await step('the old /b/ link says "This link has moved" with the agency’s contact', async () => {
      await phone.goto(`${base}/b/old-vantage-token-synthetic`);
      await phone.getByText('This link has moved').waitFor();
      await fitsThePhone(phone);
      await phone.context().close();
    });
  },
};
