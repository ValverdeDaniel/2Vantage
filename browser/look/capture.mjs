// Capturing one screen state in one app (Q.5): open it, let it settle, hide what the plan drops (old app only),
// mask dates, then take the screenshot and the measurements the comparison needs.

import path from 'node:path';

import { watch } from '../shared/chrome.mjs';
import { HEIGHT, NEW, OLD } from '../shared/config.mjs';
import { hideOnOldPage } from './hide.mjs';
import { classOrder, styles } from './measure.mjs';
import { markDates, MASK, settle } from './steady.mjs';

export function urlFor(app, screen, dealId) {
  const side = screen[app];
  if (app === 'old') {
    return side.tab ? `${OLD.base}/benefits/cases/${dealId}?tab=${side.tab}` : `${OLD.base}${side.path}`;
  }
  return side.tab ? `${NEW.base}/deals/${dealId}/${side.tab}` : `${NEW.base}${side.path}`;
}

export async function capture({ context, app, screen, dealId, width, dir, dropped }) {
  const page = await context.newPage();
  const errors = [];
  watch(page, errors, app);
  try {
    await page.setViewportSize({ width, height: HEIGHT });
    // `storage`: localStorage entries the page reads as it loads (the Advisor's ▦ Pages layout, slice 14).
    if (screen.storage) {
      await page.addInitScript((pairs) => Object.entries(pairs).forEach(([k, v]) => localStorage.setItem(k, v)), screen.storage);
    }
    const url = urlFor(app, screen, dealId);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    // `pick`: a file tab to click once the tab has drawn (Documents' census file, slice 65); absent, nothing is clicked.
    if (screen[app].pick) await page.getByRole('tab', { name: screen[app].pick }).first().click({ timeout: 30000 });
    const { readyFound } = await settle(page, screen.ready);
    const hidden = app === 'old' ? await hideOnOldPage(page, dropped) : [];
    const masked = await markDates(page);
    const file = path.join(dir, `${width}-${app}.png`);
    await page.screenshot({
      path: file,
      fullPage: true,
      animations: 'disabled',
      caret: 'hide',
      mask: [page.locator(MASK)],
      maskColor: '#FF00FF',
    });
    return {
      url,
      landed: page.url(),
      file,
      readyFound,
      hidden,
      masked,
      classes: await classOrder(page),
      styles: await styles(page, screen.styles || ['body']),
      errors,
    };
  } finally {
    await page.close();
  }
}
