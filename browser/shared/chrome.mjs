// The installed Chrome, driven through playwright-core; no browser is downloaded (devtools/e2e/README.md at 891f1b3).

import { chromium } from 'playwright-core';

import { CHROME_PATH } from './config.mjs';

export function launch({ headed = false } = {}) {
  const where = CHROME_PATH ? { executablePath: CHROME_PATH } : { channel: 'chrome' };
  return chromium.launch({ ...where, headless: !headed });
}

// Page errors and failed API answers, so a capture of a broken screen says so.
export function watch(page, errors, label) {
  page.on('pageerror', (error) => errors.push(`${label}: page error: ${error.message}`));
  page.on('response', (res) => {
    if (res.status() >= 400 && /\/api\//.test(res.url()) && !/job-status|favicon/.test(res.url())) {
      errors.push(`${label}: HTTP ${res.status()} ${new URL(res.url()).pathname}`);
    }
  });
}
