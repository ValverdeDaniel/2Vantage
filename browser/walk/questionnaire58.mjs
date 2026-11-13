// Slice 58's "done when" (plan.md §13.10 row 58; G83–G98, L91; OQ80, OQ84, OQ85): the client answers the form and
// signs as the officer. Run it with `--need s58`. It writes to GD6 (a request, the client's answers, the officer's
// signature, their approval and the filed signed copy), so seed GD6 again afterwards (`seed_golden GD6`).
//
// Staff side (signed in, through the API the Review tab uses): a request asking Florida Blue 51+ online; copy it.
// Client side, a fresh browser at 390×844 with no session: the PIN (a form online needs one, OQ80), the form's card
// with the carrier's blank, its four blanks answered (autosave), the officer's name typed and signed with Save
// progress ("Signed by … Thank you"), the to-do list saying "signed", Submit, the thank-you. Staff then find the
// answers waiting in the Questionnaire queue (OQ84), the form locked, nothing printed yet (OQ85), and Approve files the
// signed copy. Nothing on the page may be wider than the phone.

const PHONE = { width: 390, height: 844 };
const FORM = 'fl_blue_51';
const ANSWERS = [
  ['10. Has this group had Florida Blue health insurance coverage within the past 24 months?', 'No'],
  ['12. Reason for Current Bid Request', 'Renewal Increase'],
  [/^16\. Within the past 12 months/, 'No'],
];

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

const shot = async (phone, name) => {
  if (process.env.WALK_SHOTS) await phone.screenshot({ path: `${process.env.WALK_SHOTS}/${name}.png`, fullPage: true });
};

export const questionnaire58 = {
  title: 'Slice 58: the client answers the form and signs as the officer',
  deal: 'GD6',
  async run(ctx, { signIn }) {
    const { page, step, base, spec } = ctx;
    let made;
    let phone;
    let dealId;
    await signIn(ctx);
    await step('staff: GD6 gets a request asking Florida Blue 51+ online — it needs the PIN', async () => {
      const found = await api(page, base, `clients/?q=${encodeURIComponent(spec.client)}`);
      dealId = found.results.find((row) => row.name === spec.client)?.deal?.id;
      if (!dealId) throw new Error(`no deal for ${spec.client}`);
      made = await api(page, base, `deals/${dealId}/review/requests/`, 'POST', {
        people: [{ name: 'Riley Example (synthetic)' }],
        asks: { questionnaires: [{ form: FORM, mode: 'online' }] },
        message: 'Please review the questionnaire, answer what is left, and sign it — thank you!',
      });
      const link = made.links[0];
      if (link.security !== 'pin' || !/^\d{6}$/.test(link.pin)) throw new Error('a form online did not raise a PIN');
      await api(page, base, `links/${link.link_id}/`, 'PATCH', { action: 'mark_sent', copied: true });
    });
    await step('client, on a phone with no session: the PIN first, then the page and its to-do list', async () => {
      const context = await page.context().browser().newContext({ viewport: PHONE, isMobile: true, hasTouch: true, locale: 'en-US' });
      phone = await context.newPage();
      phone.setDefaultTimeout(15000);
      await phone.goto(`${base}${made.links[0].path}`);
      await phone.getByRole('heading', { name: 'This link is protected' }).waitFor();
      await phone.getByLabel('Your 6-digit PIN').fill(made.links[0].pin);
      await phone.getByRole('button', { name: 'Open', exact: true }).click();
      await phone.getByText('Your to-do list').waitFor();
      await phone.locator('.bnf-todo-item', { hasText: 'Florida Blue Underwriting Questionnaire' }).waitFor();
    });
    await step('the form’s card: its title, the carrier’s blank, the intro and the paper form, phone-wide', async () => {
      const card = phone.locator(`#bnf-sec-questionnaire_${FORM}`);
      await card.getByText('Florida Blue Underwriting Questionnaire', { exact: true }).waitFor();
      await card.getByRole('button', { name: 'View the official carrier form ▸' }).waitFor();
      await card.getByRole('button', { name: '⬇ Download blank PDF' }).waitFor();
      await card.getByText(/^Your broker has pre-filled everything we already know\./).waitFor();
      await card.getByText('Section I. General Information').waitFor();
      if (!(await card.getByLabel('Print Name of Agent/Agent Number').isDisabled())) {
        throw new Error('the agent’s own field takes the client’s typing (G86)');
      }
      await fitsThePhone(phone);
      await shot(phone, 's58-phone-form');
    });
    await step('the four blanks answered, saved automatically', async () => {
      const card = phone.locator(`#bnf-sec-questionnaire_${FORM}`);
      for (const [label, value] of ANSWERS) await card.getByLabel(label).selectOption(value);
      await card.getByLabel('Print Name of Authorized Company Officer').fill('Riley Example');
      await phone.getByText(/Saved automatically at .+ — you can come back to this link any time\.$/).waitFor({ timeout: 20000 });
      const rail = phone.locator('.bnf-todo-item', { hasText: 'Florida Blue Underwriting Questionnaire' });
      await rail.getByText(/— please sign$/).waitFor({ timeout: 20000 });
    });
    await step('the officer signs by typing their name; Save progress signs it: "Signed by Riley Example"', async () => {
      const card = phone.locator(`#bnf-sec-questionnaire_${FORM}`);
      await card.getByText(/^The undersigned Company Officer and Agent hereby acknowledges that/).waitFor();
      await card.getByLabel('Your full name, to sign').fill('Riley Example');
      await phone.getByRole('button', { name: 'Save progress' }).click();
      await card.getByText('Signed by Riley Example. Thank you — nothing further is needed on this form.').waitFor({ timeout: 20000 });
      await phone.locator('.bnf-todo-item', { hasText: 'Florida Blue Underwriting Questionnaire' }).getByText('signed', { exact: true }).waitFor();
      if (!(await card.getByLabel('12. Reason for Current Bid Request').isDisabled())) throw new Error('a signed form takes typing');
      await fitsThePhone(phone);
      await shot(phone, 's58-phone-signed');
    });
    await step('Submit, then "Thank you — sent to …"', async () => {
      const submit = phone.getByRole('button', { name: /^Submit to .+ ▸$/ });
      await submit.click();
      const again = phone.getByRole('button', { name: /still open — submit anyway\?$/ });
      if (await again.count()) await again.click();
      await phone.getByText(/^Thank you — sent to /).waitFor();
      await phone.context().close();
    });
    await step('staff: the form is signed on the link, its answers wait in the Questionnaire queue, nothing printed', async () => {
      const form = await api(page, base, `deals/${dealId}/questionnaires/${FORM}/`);
      if (!form.locked || form.officer?.name !== 'Riley Example' || form.officer?.link !== made.links[0].link_id) {
        throw new Error('the officer’s signature on the link is not on the form');
      }
      if (form.waiting < 4) throw new Error(`expected the client’s four answers waiting, found ${form.waiting}`);
      const queue = await api(page, base, `deals/${dealId}/review/queue/?surface=questionnaire`);
      const refs = queue.items.map((item) => item.ref);
      if (!refs.includes(`q:${FORM}:txtRsnBid`) || !queue.items.every((item) => item.signed)) {
        throw new Error('the signed form’s answers are not in the Questionnaire queue');
      }
    });
    await step('staff: Review & requests ▸ Questionnaire lists them; Approve all files the signed copy', async () => {
      await page.goto(`${base}/deals/${dealId}/review?view=queue&section=questionnaire`);
      await page.getByRole('button', { name: /^Questionnaire/ }).waitFor();
      await page.getByText('12. Reason for Current Bid Request').first().waitFor();
      await api(page, base, `deals/${dealId}/review/approve/`, 'POST', { surface: 'questionnaire', ready_only: false });
      const form = await api(page, base, `deals/${dealId}/questionnaires/${FORM}/`);
      if (form.waiting !== 0 || form.values.txtRsnBid !== 'Renewal Increase') throw new Error('the approval did not land');
      const docs = await api(page, base, `deals/${dealId}/documents/`);
      if (!docs.some((doc) => doc.label === 'Florida Blue 51+ — signed copy')) throw new Error('no signed copy was filed');
    });
  },
};
