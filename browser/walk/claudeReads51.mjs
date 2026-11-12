// Slice 51's "done when" (plan.md §13.10 row 51; C11, C19, D29, D41, D110, D112, D134, B40): Claude's census and intake
// readers on a fresh prospect. Intake's ✦ Work with Claude opens the drawer; a synthetic company profile dropped there
// is read and waits in Intake's review; "Use this scan ▸" fills the form. On the empty Census tab "Scan the census with
// Claude ▸" opens the drawer; a synthetic PDF roster dropped there is read and waits as a staged census import ("A
// census file is waiting for review"); "Review it on the Census tab ▸" opens it in the mapping dialog, read by Claude,
// and its dry run and Apply put the people on the roster.
//
// Run it with `--need s51` as an admin (golden-admin). Each run makes one prospect, "Walk51 Claude reads (synthetic)",
// archived at the end, and TWO REAL Claude reads (Sonnet 5.5, a few cents of the build's $20 cap, `manage.py
// ai_spend`); the backend needs ANTHROPIC_API_KEY, the PHI-gate switch on (AI_PHI_READERS, the dev stack's) and the
// worker running. Every file is made here, synthetic: no real client's file.

const READ_MS = 300000;
const NAME = 'Walk51 Claude reads (synthetic)';

// The roster and the profile, as text pages (the census: two families and a single employee).
const ROSTER = [
  'Walk51 Manufacturing (synthetic) - employee census, effective 01/01/2027',
  'Employee / Dependent        Rel      DOB          Sex   ZIP     Medical tier',
  'Avery Testworth             EE       04/12/1981   F     33601   Family',
  '  Rowan Testworth           Spouse   09/30/1980   M',
  '  Kit Testworth             Child    02/14/2014   F',
  'Morgan Samplefield          EE       11/02/1975   M     33602   Employee + Spouse',
  '  Dana Samplefield          Spouse   06/21/1977   F',
  'Jules Exampleton            EE       07/07/1990   F     33603   Employee Only',
];
const PROFILE = [
  'Walk51 Manufacturing LLC (synthetic) - company profile',
  'Legal name: Walk51 Manufacturing LLC',
  'FEIN: 12-3456789',
  'Physical address: 100 Example Way, Tampa, FL 33601',
  'Total employees: 3',
  'Current medical: Example Health Plan, fully insured, renews 01/01/2027',
  'Benefits contact: Jordan Example, HR Manager, jordan@example.com',
];

function escapePdf(text) {
  return text.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
}

// A one-page PDF with a real text layer (Helvetica): the walk's own synthetic file, as synthetic_files.pdf writes one.
function pdfOf(lines) {
  const ops = lines.map((text, i) => `BT /F1 10 Tf 54 ${740 - 16 * i} Td (${escapePdf(text)}) Tj ET`).join('\n');
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [4 0 R] /Count 1 >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>',
    `<< /Length ${ops.length} >>\nstream\n${ops}\nendstream`,
  ];
  let out = '%PDF-1.4\n';
  const offsets = objects.map((body, i) => {
    const at = out.length;
    out += `${i + 1} 0 obj\n${body}\nendobj\n`;
    return at;
  });
  const xref = out.length;
  out += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  out += offsets.map((at) => `${String(at).padStart(10, '0')} 00000 n \n`).join('');
  out += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out, 'latin1').toString('base64');
}

async function dropPdf(page, name, b64) {
  await page.evaluate(
    ({ name, b64 }) => {
      const transfer = new DataTransfer();
      transfer.items.add(new File([Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))], name, { type: 'application/pdf' }));
      const target = document.querySelector('[data-claude-panel]');
      ['dragenter', 'dragover', 'drop'].forEach((type) =>
        target.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: transfer })),
      );
    },
    { name, b64 },
  );
}

export const claudeReads51 = {
  title: 'Claude reads a census roster and a company profile: both wait for review; the census lands on the Census tab',
  deal: 'GD6',
  async run(ctx, { signIn }) {
    const { page, step, base } = ctx;
    let dealId;
    const drawer = page.getByRole('dialog', { name: 'Work with Claude' });
    await signIn(ctx);
    await step('＋ New deal makes a prospect and opens its Intake', async () => {
      await page.getByRole('button', { name: /New deal/ }).click();
      await page.waitForURL(/\/deals\/new/);
      await page.getByLabel('Group name *').fill(NAME);
      await page.getByRole('button', { name: /Create deal & open intake/ }).click();
      await page.waitForURL(/\/deals\/\d+\/intake/, { timeout: 30000 });
      dealId = page.url().match(/\/deals\/(\d+)/)[1];
    });
    await step('Intake’s ✦ Work with Claude opens the drawer (D134)', async () => {
      await page.getByRole('button', { name: '✦ Work with Claude' }).click();
      await drawer.waitFor();
    });
    await step('a company profile dropped there is read and waits in Intake’s review (B40, D112)', async () => {
      await dropPdf(page, 'company-profile.pdf', pdfOf(PROFILE));
      await drawer.getByText('Review this scan').waitFor({ timeout: READ_MS });
      await drawer.getByText('Legal Company Name').first().waitFor();
      await drawer.getByText('Walk51 Manufacturing LLC').first().waitFor();
    });
    await step('Use this scan ▸ fills the form, its values Claude’s', async () => {
      await drawer.getByRole('button', { name: 'Use this scan ▸' }).click();
      await page.getByText(/Scan applied — /).first().waitFor({ timeout: 30000 });
      const intake = await page.evaluate(
        async ({ base, dealId }) => (await fetch(`${base}/api/deals/${dealId}/intake/`)).json(),
        { base, dealId },
      );
      if (intake.answers.legal_name !== 'Walk51 Manufacturing LLC') throw new Error('legal name not filled');
      if (intake.sources.legal_name.origin !== 'ai') throw new Error('legal name is not Claude’s');
      await drawer.getByRole('button', { name: /Close/ }).first().click();
    });
    await step('the empty Census tab offers "Scan the census with Claude ▸", which opens the drawer (D41)', async () => {
      await page.getByRole('link', { name: 'Census', exact: true }).click();
      await page.waitForURL(/\/census/);
      const door = page.getByRole('button', { name: 'Scan the census with Claude ▸' });
      await door.waitFor();
      if (!(await drawer.isVisible())) await door.click();
      await drawer.waitFor();
    });
    await step('a PDF roster dropped there is read and waits as a census import (C11, C19, D110)', async () => {
      await dropPdf(page, 'roster.pdf', pdfOf(ROSTER));
      await drawer.getByText('A census file is waiting for review').waitFor({ timeout: READ_MS });
      await drawer.getByText(/was read, not applied: 6 people \(3 employees, 3 dependents\)/).waitFor();
    });
    await step('"Review it on the Census tab ▸" opens it in the mapping dialog, read by Claude (D29)', async () => {
      await drawer.getByRole('button', { name: 'Review it on the Census tab ▸' }).click();
      await page.getByText('Map census columns').waitFor();
      await page.getByText(/read by Claude · 6 people/).waitFor();
    });
    await step('its dry run lists 6 people added, and Apply puts them on the roster', async () => {
      await page.getByRole('button', { name: /Apply mapping & build roster/ }).click();
      await page.getByText(/6 added · 0 changed · 0 removed · 0 kept/).waitFor({ timeout: 30000 });
      await page.getByRole('button', { name: /Apply to the roster/ }).click();
      await page.getByText(/3 employees · 3 dependents/).first().waitFor({ timeout: 30000 });
    });
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
  },
};
