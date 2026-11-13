// Slice 59's "done when" (plan.md §13.10 row 59; D44, L99, L111, L125, L135; OQ89): a client's census file becomes a
// staged import that staff apply. Run it with `--need s59` as an admin (golden-admin).
//
// Staff (signed in, through the API the Review tab uses): a fresh prospect, "Walk59 Client census (synthetic)", and a
// request asking only for its census file (an upload-only ask: no PIN, OQ80). Client, a fresh browser at 390×844 with
// no session: the page asks for the census file; they attach a synthetic CSV and Submit; the thank-you is followed by
// the receipt ("What you sent": the census file, with the time; never the file's name, often the people's, §3.8). The
// upload starts the census reader with no person ("Client portal"); a spreadsheet in our own columns is mapped in
// code, so this walk sends nothing to Claude ($0; the worker must be running and the PHI-gate switch on, as in the dev
// stack). Staff: the Review tab's To review lane says "Their census file was read" (and lists the file by its slot,
// never its name); "Review and apply ▸" opens the staged import in the Census tab's mapping dialog; its dry run lists
// 3 added and Apply puts them on the roster; the row is gone and the file reads "used". The prospect is archived at
// the end; no golden deal is touched.

const PHONE = { width: 390, height: 844 };
const READ_MS = 120000;
const NAME = 'Walk59 Client census (synthetic)';
const FILE = 'Walk59 census (synthetic).csv';
const CSV = [
  'First Name,Last Name,Relationship,Date of Birth,Gender,Zip Code,Medical Tier',
  'Avery,Walkfiftynine,Employee,04/12/1981,F,33601,Employee + Spouse',
  'Rowan,Walkfiftynine,Spouse,09/30/1980,M,,',
  'Jules,Samplefield,Employee,07/07/1990,F,33603,Employee Only',
].join('\r\n');

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

const readRow = (board) => (board.lanes?.to_review || []).find((row) => row.key.startsWith('read:'));
const filesRow = (board) => (board.lanes?.to_review || []).find((row) => row.key === 'documents');

export const clientReads59 = {
  title: "Slice 59: a client's census file becomes a staged import that staff apply",
  deal: null,
  async run(ctx, { signIn }) {
    const { page, step, base } = ctx;
    let dealId;
    let made;
    let phone;
    await signIn(ctx);
    try {
      await step('staff: a fresh prospect and a request for its census file only (no PIN)', async () => {
        await page.getByRole('button', { name: /New deal/ }).click();
        await page.waitForURL(/\/deals\/new/);
        await page.getByLabel('Group name *').fill(NAME);
        await page.getByRole('button', { name: /Create deal & open intake/ }).click();
        await page.waitForURL(/\/deals\/\d+\/intake/, { timeout: 30000 });
        dealId = page.url().match(/\/deals\/(\d+)/)[1];
        made = await api(page, base, `deals/${dealId}/review/requests/`, 'POST', {
          people: [{ name: 'Riley Example (synthetic)' }],
          asks: { census: { file: true } },
          message: 'Your employee census, please — thank you!',
        });
        if (made.links[0].security !== 'link') throw new Error('an upload-only ask raised a PIN');
        await api(page, base, `links/${made.links[0].link_id}/`, 'PATCH', { action: 'mark_sent', copied: true });
      });
      await step('client, on a phone with no session: the page asks for their census file', async () => {
        const context = await page.context().browser().newContext({ viewport: PHONE, isMobile: true, hasTouch: true, locale: 'en-US' });
        phone = await context.newPage();
        phone.setDefaultTimeout(15000);
        await phone.goto(`${base}${made.links[0].path}`);
        await phone.getByText('Your employee census, please — thank you!').waitFor();
        await phone.getByText('Attach your census file').waitFor();
        await phone.getByLabel('Upload Attach your census file').waitFor({ state: 'attached' }); // a hidden file input
      });
      await step('they attach the census file and Submit: the thank-you, then the receipt with the file and the time', async () => {
        await phone.getByLabel('Upload Attach your census file').setInputFiles({ name: FILE, mimeType: 'text/csv', buffer: Buffer.from(CSV) });
        await phone.getByRole('button', { name: /^Submit to .+ ▸$/ }).click();
        const again = phone.getByRole('button', { name: /still open — submit anyway\?$/ });
        if (await again.count()) await again.click();
        await phone.getByText(/^Thank you — sent to /).waitFor({ timeout: 30000 });
        const receipt = phone.getByRole('region', { name: 'What you sent' });
        await receipt.getByText(/^Sent .+ at .+$/).waitFor();
        await receipt.getByText('Employee census file', { exact: true }).waitFor();
        if (await receipt.getByText(FILE).count()) throw new Error('the receipt names the file: file names are PHI');
        await phone.getByRole('button', { name: 'Back to the form ▸' }).waitFor();
        const wide = await phone.evaluate(() => document.documentElement.scrollWidth);
        if (wide > 391) throw new Error(`the receipt is ${wide}px wide on a 390px screen`);
        if (process.env.WALK_SHOTS) await phone.screenshot({ path: `${process.env.WALK_SHOTS}/s59-phone-receipt.png` });
      });
      await step('the upload started the census reader with no person: it is read and staged for a person', async () => {
        const until = Date.now() + READ_MS;
        let board = await api(page, base, `deals/${dealId}/review/board/`);
        while (!readRow(board) && Date.now() < until) {
          await page.waitForTimeout(2000);
          board = await api(page, base, `deals/${dealId}/review/board/`);
        }
        if (!readRow(board)) throw new Error('no staged read of the client’s census file came');
        const ai = await api(page, base, `deals/${dealId}/ai/`);
        const job = [...(ai.recent || []), ...(ai.jobs || [])].find((one) => one.target === 'census');
        if (job && (job.created_by || job.actor_label !== 'Client portal')) throw new Error('the read was not the portal’s');
      });
      await step('staff: the To review lane says "Their census file was read" with Review and apply ▸', async () => {
        await page.goto(`${base}/deals/${dealId}/review`);
        await page.getByText('Their census file was read').waitFor({ timeout: 30000 });
        await page.getByText('Read — waiting for review').first().waitFor();
        if (await page.getByText(FILE).count()) throw new Error('the Board names the file: file names are PHI');
        if (process.env.WALK_SHOTS) await page.screenshot({ path: `${process.env.WALK_SHOTS}/s59-board.png` });
      });
      await step('Review and apply ▸ opens the staged import in the mapping dialog', async () => {
        await page.getByRole('button', { name: 'Review and apply ▸' }).click();
        await page.waitForURL(/\/census/);
        await page.getByText('Map census columns').waitFor({ timeout: 30000 });
      });
      await step('its dry run lists 3 people added, and Apply puts them on the roster', async () => {
        await page.getByRole('button', { name: /Apply mapping & build roster/ }).click();
        await page.getByText(/3 added · 0 changed · 0 removed · 0 kept/).waitFor({ timeout: 30000 });
        await page.getByRole('button', { name: /Apply to the roster/ }).click();
        await page.getByText(/2 employees · 1 dependent/).first().waitFor({ timeout: 30000 });
      });
      await step('the read row is gone from To review, and the file reads "used"', async () => {
        const board = await api(page, base, `deals/${dealId}/review/board/`);
        if (readRow(board)) throw new Error('the applied read still waits on the Board');
        const file = (filesRow(board)?.files || []).find((one) => one.label === 'Census file');
        if (!file || file.read !== 'used') throw new Error(`the census file reads "${file?.read}", not "used"`);
      });
    } finally {
      if (phone) await phone.context().close();
      if (dealId) {
        // tidy: archive the walk's prospect (slice 38's archive; best effort)
        await page.evaluate(
          async ({ base, dealId }) => {
            const deal = await (await fetch(`${base}/api/deals/${dealId}/`)).json();
            const token = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
            await fetch(`${base}/api/clients/${deal.client.id}/archive/`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
              body: JSON.stringify({ archived: true }),
            });
          },
          { base, dealId },
        );
      }
    }
  },
};
