// Slice 65's "done when" (plan.md §13.10 row 65; E25, E43–E45, E69–E71, D128, D130; OQ97–OQ99): "The census file
// opens beside its roster; a scanned SBC page highlights its values; the pop-out follows the keys". Run it with
// `--need s65`. On GD4's Documents tab:
// - the client's census file opens with the whole roster under it, and a cell's ↗ rings the cell in the workbook;
// - P1's scanned SBC (a picture, no text layer) has its deductible and out-of-pocket limit boxed by browser OCR, whose
//   files come from our own origin; "Check this file" leaves them to the eye, and the box still draws;
// - ⧉ New window opens the file in its own window, linked; F, C and U pressed there act on the tab's selection and the
//   window follows; when the tab leaves the client the window says so, and comes back with it; "Bring it back here".
// It writes review marks and the locator's answers on GD4 (each undone or harmless): re-seed GD4 after it.

const SETTLED = ['ocr', 'missing', 'found', 'moved'];

/** What the viewer's find settled on (it says so on `data-find`), once OCR has had its time. */
async function viewerState(page) {
  const read = (settled) => {
    const state = document.querySelector('[data-viewer-doc] [data-find]')?.getAttribute('data-find');
    return settled.includes(state) ? state : null;
  };
  return (await page.waitForFunction(read, SETTLED, { timeout: 90000 })).jsonValue();
}

export const documents65 = {
  title: 'Slice 65: the census file beside its roster; a scanned SBC highlights its values; the pop-out follows the keys',
  deal: 'GD4',
  async run(ctx, { signIn, openDeal }) {
    const { page, step, spec } = ctx;
    const p1 = spec.plans.find((plan) => plan.ref === 'P1');
    const requests = [];
    page.on('request', (request) => requests.push(request.url()));
    const fileBar = (what) => page.getByText(`Opened to show ${what}`);
    const listRow = (label) => page.getByRole('option').filter({ hasText: label });
    await signIn(ctx);
    await openDeal(ctx);

    await step("the Documents tab opens GD4's census file with the whole roster beside it", async () => {
      await page.getByRole('link', { name: 'Documents', exact: true }).click();
      await page.getByRole('tab', { name: /census \(synthetic\)\.xlsx/ }).click();
      await page.getByText(/^‘?Census’?$|Rows 1–/).first().waitFor();
      await page.getByRole('grid', { name: 'Census roster' }).waitFor();
      await page.getByText(/100 employees · 60 dependents · the whole roster/).waitFor();
    });
    await step("a roster cell's ↗ rings that cell in the workbook above", async () => {
      const cell = page.getByRole('gridcell', { name: /^Ashfield/ }).first();
      await cell.hover();
      await cell.getByRole('button', { name: 'View in document' }).click();
      await fileBar('Last Name').waitFor();
      await page.getByText(/^Found in .Census. D2$/).waitFor();
      await page.getByRole('grid', { name: 'Census roster' }).waitFor(); // the roster stays under the file
    });

    await step(`P1's scanned SBC: browser OCR boxes its deductible (${p1.values.deductible_single})`, async () => {
      await page.getByRole('tab', { name: /SBC, scanned/ }).click();
      await listRow('Deductible (Single)').dblclick();
      await fileBar(`Deductible (Single) · Aetna ${p1.name}`).waitFor();
      if ((await viewerState(page)) !== 'ocr') throw new Error('the deductible was not boxed');
      await page.getByText('✓ Located on the scanned image').waitFor();
    });
    await step('and its out-of-pocket limit, from files served by our own origin only', async () => {
      await listRow('OOP Max (Single)').dblclick();
      await fileBar(`OOP Max (Single) · Aetna ${p1.name}`).waitFor();
      if ((await viewerState(page)) !== 'ocr') throw new Error('the out-of-pocket limit was not boxed');
      const ocr = requests.filter((url) => /tesseract|traineddata|\/ocr\//.test(url));
      if (!ocr.length || ocr.some((url) => !url.startsWith(ctx.base))) throw new Error(`OCR files: ${ocr.join(', ')}`);
    });
    await step('"Check this file" leaves the scan to the eye: OCR draws, it never marks a value found', async () => {
      await page.getByRole('button', { name: /^Check this file/ }).click();
      await page.getByText(/Checked 2 values against the file/).first().waitFor({ timeout: 60000 });
      await page.getByRole('button', { name: /^Check by eye/ }).waitFor();
      if (await page.getByRole('button', { name: /^Found in the file/ }).count()) throw new Error('a scanned value reads found');
      await listRow('Deductible (Single)').dblclick();
      await fileBar(`Deductible (Single) · Aetna ${p1.name}`).waitFor();
      await page.getByText('Check by eye', { exact: true }).first().waitFor();
      if ((await viewerState(page)) !== 'ocr') throw new Error('the box went with the check');
    });

    let popup = null;
    await step('⧉ New window opens the file in its own window, linked, naming the client', async () => {
      await listRow('OOP Max (Single)').click();
      [popup] = await Promise.all([
        page.context().waitForEvent('page'),
        page.getByRole('button', { name: '⧉ New window' }).click(),
      ]);
      await popup.getByText(spec.client).first().waitFor();
      await popup.getByText('Linked to the Documents tab in your other window').waitFor();
      await page.getByText(/is open in its own window/).waitFor();
    });
    await step('F pressed in the window opens the selected value there, boxed', async () => {
      await popup.bringToFront();
      await popup.locator('body').click({ position: { x: 5, y: 5 } });
      await popup.keyboard.press('f');
      await popup.getByText(`Showing OOP Max (Single) · Aetna ${p1.name}`).waitFor();
      if ((await viewerState(popup)) !== 'ocr') throw new Error('the window did not box it');
    });
    await step("C and U pressed in the window mark and clear the tab's value", async () => {
      await popup.keyboard.press('c');
      await page.getByText(/1 value flagged as needing checking/).first().waitFor();
      await popup.keyboard.press('u');
      await page.getByText(/1 value unmarked/).first().waitFor();
    });
    await step('the tab leaving the client covers the window; coming back clears it', async () => {
      await page.bringToFront();
      await page.goto(`${ctx.base}/`);
      await popup.getByText(`You’re no longer working on ${spec.client}`).waitFor({ timeout: 10000 });
      await page.goBack();
      await popup.getByText('Linked to the Documents tab in your other window').waitFor({ timeout: 15000 });
      if (await popup.getByText(/no longer working on/).count()) throw new Error('the cover stayed');
    });
    await step('"Bring it back here" closes the window and the file shows on the tab again', async () => {
      const closing = popup.waitForEvent('close', { timeout: 10000 });
      await page.getByRole('button', { name: 'Bring it back here' }).click();
      await closing;
      await page.getByRole('button', { name: '⧉ New window' }).waitFor();
    });
  },
};
