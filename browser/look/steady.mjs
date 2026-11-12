// Determinism for the Look lane (Q.5): one fixed clock, no animation, fonts loaded, dates masked, on both apps alike.

import { FIXED_NOW } from '../shared/config.mjs';

const STILL = `
*, *::before, *::after {
  animation-duration: 0s !important; animation-delay: 0s !important; animation-iteration-count: 1 !important;
  transition: none !important; caret-color: transparent !important; scroll-behavior: auto !important;
}`;

// Dates and times a screen prints from "now" or from row stamps (created, updated, "3 days ago").
const DATE_PATTERNS = [
  String.raw`\b\d{1,2}/\d{1,2}/\d{2,4}\b`,
  String.raw`\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?\b`,
  String.raw`\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.? \d{1,2}(?:, \d{4})?\b`,
  String.raw`\b\d{1,2}:\d{2}(?:\s?[AaPp]\.?[Mm]\.?)?\b`,
  String.raw`\b(?:\d+|an?|one) (?:second|minute|hour|day|week|month|year)s? ago\b`,
  String.raw`\b(?:just now|today|yesterday)\b`,
];

export async function prepareContext(context) {
  await context.clock.setFixedTime(new Date(FIXED_NOW));
}

export async function settle(page, ready) {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  let readyFound = !ready;
  if (ready) {
    readyFound = await page.waitForSelector(ready, { timeout: 15000 }).then(() => true, () => false);
  }
  await page.addStyleTag({ content: STILL });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  return { readyFound };
}

// Tag the smallest elements whose own text looks like a date, so the screenshot masks them on both sides.
export async function markDates(page) {
  return page.evaluate((patterns) => {
    const re = new RegExp(patterns.join('|'), 'i');
    let count = 0;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const host = node.parentElement;
      if (host && !host.closest('script,style') && re.test(node.textContent)) {
        host.setAttribute('data-look-mask', '');
        count += 1;
      }
    }
    for (const input of document.querySelectorAll('input[type="date"], input[type="datetime-local"]')) {
      input.setAttribute('data-look-mask', '');
      count += 1;
    }
    return count;
  }, DATE_PATTERNS);
}

export const MASK = '[data-look-mask]';
