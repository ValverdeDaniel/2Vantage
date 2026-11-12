// Need 1 through the quote-first door (plan.md §13.7 row 20, "done when"; V.2 need 1; A14, D43, D71, D73, D35): from
// ＋ New deal, "I already have carrier quotes" opens Work with Claude on the page; a carrier file dropped on it makes
// the deal, is filed and read at once, and the deal opens on its Advisor with the drawer; an admin's read lands by
// itself ("✓ Claude's read landed — …", the plans on the board, the deal at Quoting, its lines added) and ↶ Undo this
// run takes it back. The file is GD3's synthetic renewal packet, fetched from the seeded deal.
//
// Run it with `--need 1q` as an admin (the lane's golden-admin). Each run makes one prospect, "Walk 1q quote-first
// (synthetic)", archived at the end, and ONE REAL Claude read (Sonnet 5.5, about $0.04 of the build's $20 cap,
// `manage.py ai_spend`); the backend needs ANTHROPIC_API_KEY and the worker must be running.

const READ_MS = 300000;

async function fetchPacket(page, base, client) {
  return page.evaluate(
    async ({ base, client }) => {
      const json = async (url) => (await fetch(`${base}/api/${url}`)).json();
      const clients = await json(`clients/?q=${encodeURIComponent(client)}`);
      const row = (clients.results || clients).find((entry) => entry.name === client);
      const docs = await json(`deals/${row.deal.id}/documents/`);
      const packet = docs.find((doc) => doc.kind === 'renewal');
      const bytes = new Uint8Array(await (await fetch(`${base}/api/documents/${packet.id}/download/`)).arrayBuffer());
      let text = '';
      bytes.forEach((byte) => {
        text += String.fromCharCode(byte);
      });
      return btoa(text);
    },
    { base, client },
  );
}

async function dropPdf(page, selector, name, b64) {
  await page.evaluate(
    ({ selector, name, b64 }) => {
      const transfer = new DataTransfer();
      transfer.items.add(new File([Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))], name, { type: 'application/pdf' }));
      const target = document.querySelector(selector);
      ['dragenter', 'dragover', 'drop'].forEach((type) =>
        target.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: transfer })),
      );
    },
    { selector, name, b64 },
  );
}

export const quoteDoor20 = {
  title: 'Scan quotes through the quote-first door: dropped files make the deal and an admin’s read lands, with Undo (A14, D43, D71)',
  deal: 'GD3',
  async run(ctx, { signIn }) {
    const { page, step, spec, base } = ctx;
    const name = 'Walk 1q quote-first (synthetic)';
    let dealId;
    await signIn(ctx);
    const packet = await fetchPacket(page, base, spec.client);
    await step('＋ New deal opens the New deal page; "I already have carrier quotes" opens Work with Claude', async () => {
      await page.getByRole('button', { name: /New deal/ }).click();
      await page.waitForURL(/\/deals\/new/);
      await page.getByRole('button', { name: /I already have carrier quotes/ }).click();
      await page.getByRole('dialog', { name: 'Work with Claude' }).waitFor();
      await page.getByLabel('Group name *').fill(name);
    });
    await step('the dropped file makes the deal, is read, and the deal opens on its Advisor with the drawer', async () => {
      await dropPdf(page, '[data-claude-panel]', 'renewal-packet.pdf', packet);
      await page.waitForURL(/\/deals\/\d+\/advisor\?claude=1/, { timeout: 60000 });
      dealId = page.url().match(/\/deals\/(\d+)/)[1];
      await page.getByRole('dialog', { name: 'Work with Claude' }).waitFor();
    });
    await step('an admin’s read lands by itself: the plans, Quoting, and ↶ Undo this run', async () => {
      await page.getByText(/✓ Claude’s read landed — 2 current plans · 2 renewals/).first().waitFor({ timeout: READ_MS });
      await page.getByText('Quoting', { exact: true }).first().waitFor();
      const [first, second] = spec.arrivals.map((plan) => plan.name);
      await page.getByText(first).filter({ visible: true }).first().waitFor();
      await page.getByText(second).filter({ visible: true }).first().waitFor();
    });
    await step('↶ Undo this run takes the plans off again', async () => {
      const drawer = page.getByRole('dialog', { name: 'Work with Claude' });
      await drawer.getByRole('button', { name: '↶ Undo this run' }).click();
      await page.getByRole('dialog', { name: /Undo this run/ }).getByRole('button', { name: 'Undo this run', exact: true }).click();
      await page.getByText(/Undone — the deal is back to how it was before that read/).waitFor({ timeout: 30000 });
    });
    if (dealId) {
      // tidy: archive the walk's prospect so the Prospects list does not grow (slice 38's archive; best effort)
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
  },
};
