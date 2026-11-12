// Slice 34's "done when" (plan.md §13.8 row 34; J32–J35, J43, J155): on GD1's Proposal builder, an uploaded cover
// and a team member print on the PDF and the PowerPoint. The walk uploads a synthetic cover on the Cover card (picked
// at once), adds a person in the Firm pages drawer, sees them ticked on the Presentation pages card, downloads both
// files and finds the new picture and the person's name in them; then it deletes the person and the upload and puts
// GD1's cover back, as it found it. Run with `--need s34`. The backend tests read the files closely
// (proposals/tests/test_cover_print.py).

import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';

const PERSON = 'Walk Person (synthetic)';

// A flat-colour PNG, made here: the walk carries no picture file.
function png(width, height, [r, g, b]) {
  const chunk = (type, data) => {
    const body = Buffer.concat([Buffer.from(type), data]);
    const length = Buffer.alloc(4);
    length.writeUInt32BE(data.length);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(zlib.crc32(body) >>> 0);
    return Buffer.concat([length, body, crc]);
  };
  const head = Buffer.alloc(13);
  head.writeUInt32BE(width, 0);
  head.writeUInt32BE(height, 4);
  head.set([8, 2, 0, 0, 0], 8);
  const row = Buffer.concat([Buffer.from([0]), Buffer.from(Array.from({ length: width }, () => [r, g, b]).flat())]);
  const pixels = zlib.deflateSync(Buffer.concat(Array.from({ length: height }, () => row)));
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  return Buffer.concat([signature, chunk('IHDR', head), chunk('IDAT', pixels), chunk('IEND', Buffer.alloc(0))]);
}

// ASCII85 (reportlab writes its page streams as ASCII85 over Flate): the bytes, or null when it is not ASCII85.
function ascii85(body) {
  const text = body.toString('latin1').replace(/\s+/g, '');
  if (!text.endsWith('~>')) return null;
  const out = [];
  let group = [];
  const flush = (count) => {
    let value = group.reduce((sum, digit) => sum * 85 + digit, 0);
    const bytes = [];
    for (let i = 3; i >= 0; i -= 1) {
      bytes[i] = value % 256;
      value = Math.floor(value / 256);
    }
    out.push(...bytes.slice(0, count));
  };
  for (const char of text.slice(0, -2)) {
    if (char === 'z' && !group.length) {
      out.push(0, 0, 0, 0);
      continue;
    }
    group.push(char.charCodeAt(0) - 33);
    if (group.length === 5) {
      flush(4);
      group = [];
    }
  }
  if (group.length) {
    const count = group.length - 1;
    while (group.length < 5) group.push(84);
    flush(count);
  }
  return Buffer.from(out);
}

// Every stream of a PDF, decoded where it is ASCII85 or deflated: its text operators and its pictures' bytes.
function pdfStreams(file) {
  const raw = fs.readFileSync(file);
  const text = raw.toString('latin1');
  const out = [];
  for (const match of text.matchAll(/stream\r?\n/g)) {
    const start = match.index + match[0].length;
    const end = text.indexOf('endstream', start);
    let body = raw.subarray(start, end);
    body = ascii85(body) ?? body;
    try {
      out.push(zlib.inflateSync(body));
    } catch {
      out.push(body);
    }
  }
  return out;
}

// Every part of a .pptx (a zip), by name, inflated.
function zipParts(file) {
  const raw = fs.readFileSync(file);
  const parts = {};
  let at = 0;
  while (raw.readUInt32LE(at) === 0x04034b50) {
    const method = raw.readUInt16LE(at + 8);
    const size = raw.readUInt32LE(at + 18);
    const nameLength = raw.readUInt16LE(at + 26);
    const extra = raw.readUInt16LE(at + 28);
    const name = raw.subarray(at + 30, at + 30 + nameLength).toString('utf8');
    const data = raw.subarray(at + 30 + nameLength + extra, at + 30 + nameLength + extra + size);
    parts[name] = method === 8 ? zlib.inflateRawSync(data) : data;
    at += 30 + nameLength + extra + size;
  }
  return parts;
}

const hash = (data) => crypto.createHash('sha1').update(data).digest('hex');

async function download(page, button, ext) {
  const got = page.waitForEvent('download', { timeout: 90000 });
  await page.getByRole('button', { name: button }).click();
  const file = path.join(os.tmpdir(), `walk-s34-${Date.now()}.${ext}`);
  await (await got).saveAs(file);
  return file;
}

function slideOne(parts) {
  const rels = parts['ppt/slides/_rels/slide1.xml.rels'].toString('utf8');
  return [...rels.matchAll(/Target="\.\.\/media\/([^"]+)"/g)].map((m) => hash(parts[`ppt/media/${m[1]}`]));
}

// A builder card, opened if it starts collapsed (a completed card does).
async function openCard(page, guide) {
  const card = page.locator(`[data-guide="${guide}"]`);
  const toggle = card.locator('.bnf-bcard-toggle');
  await toggle.waitFor();
  if ((await toggle.getAttribute('aria-expanded')) === 'false') await toggle.click();
  return card;
}

export const cover34 = {
  title: 'The Proposal builder on GD1: an uploaded cover and a team member print on the PDF and the PowerPoint',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step } = ctx;
    page.on('dialog', (dialog) => dialog.accept());
    const before = {};
    await signIn(ctx);
    await openDeal(ctx);
    await step('the builder opens with its Cover card: the Vantage tile, picked, and "Upload a cover"', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'Proposal builder' }).click();
      const cover = await openCard(page, 'build-cover');
      await cover.getByRole('button', { name: 'Vantage', pressed: true }).waitFor();
      await cover.getByText('Upload a cover').waitFor();
    });
    await step('the PDF and the PowerPoint as GD1 has them now (to compare with)', async () => {
      before.pdf = new Set(pdfStreams(await download(page, '⬇ Client PDF', 'pdf')).map(hash));
      before.slide = new Set(slideOne(zipParts(await download(page, '⬇ PowerPoint', 'pptx'))));
    });
    await step('a cover uploaded on the Cover card is picked at once', async () => {
      const cover = page.locator('[data-guide="build-cover"]');
      await cover.locator('input[type="file"]').setInputFiles({ name: 'walk-cover.png', mimeType: 'image/png', buffer: png(640, 420, [0x22, 0x77, 0xaa]) });
      await page.getByText('Cover image added and picked for this proposal').waitFor();
      await cover.locator('.bnf-cover-tile-on').getByText(/Your image \d+/).waitFor();
      await cover.getByText('· also tops the spreadsheet').waitFor();
    });
    await step('"Edit the firm pages ▸" opens the drawer, where a person is added to the team', async () => {
      await page.getByRole('button', { name: 'Edit the firm pages ▸' }).click();
      const drawer = page.getByRole('dialog', { name: 'Firm pages' });
      await drawer.getByLabel("New team member's name").fill(PERSON);
      await drawer.getByRole('button', { name: '＋ Add a person' }).click();
      await drawer.locator(`.bnf-firm-person input[value="${PERSON}"]`).waitFor();
      await drawer.getByRole('button', { name: 'Close Firm pages' }).click();
    });
    await step("the person is ticked on this client's team, and the ledger says the team page prints", async () => {
      const pages = await openCard(page, 'build-pages');
      const tick = pages.getByRole('checkbox', { name: PERSON, exact: true });
      await tick.waitFor();
      if (!(await tick.isChecked())) throw new Error('the person is not ticked');
      await pages.locator('.bnf-present-row', { hasText: 'Your team' }).getByText('prints').waitFor();
    });
    await step('the PDF prints the uploaded cover and the person', async () => {
      const streams = pdfStreams(await download(page, '⬇ Client PDF', 'pdf'));
      if (!streams.some((data) => data.toString('latin1').includes('Walk Person'))) throw new Error('the person is not in the PDF');
      if (!streams.some((data) => !before.pdf.has(hash(data)) && data[0] === 0xff && data[1] === 0xd8)) {
        throw new Error('no new picture in the PDF');
      }
    });
    await step('the PowerPoint prints the uploaded cover on its first slide and the person on a slide', async () => {
      const parts = zipParts(await download(page, '⬇ PowerPoint', 'pptx'));
      if (!slideOne(parts).some((digest) => !before.slide.has(digest))) throw new Error('slide 1 wears no new picture');
      const slides = Object.keys(parts).filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name));
      if (!slides.some((name) => parts[name].toString('utf8').includes(PERSON))) throw new Error('the person is not on a slide');
    });
    await step('putting GD1 back: the person removed, the upload deleted, the Vantage cover picked', async () => {
      await page.getByRole('button', { name: 'Edit the firm pages ▸' }).click();
      const drawer = page.getByRole('dialog', { name: 'Firm pages' });
      const person = drawer.locator('.bnf-firm-person', { has: page.locator(`[value="${PERSON}"]`) });
      await person.getByRole('button', { name: 'Remove from the team' }).click();
      await person.waitFor({ state: 'detached' });
      await drawer.getByRole('button', { name: 'Close Firm pages' }).click();
      const cover = page.locator('[data-guide="build-cover"]');
      await cover.locator('.bnf-cover-tile-on .bnf-cover-del').click();
      await page.getByText('Cover image deleted').waitFor();
      await cover.getByRole('button', { name: 'Vantage', pressed: true }).waitFor();
    });
  },
};
