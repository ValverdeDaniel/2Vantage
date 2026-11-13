// The golden specs and keys, read from the same files 2Vantage's seed and the old loader read (golden/specs.py).

import fs from 'node:fs';
import path from 'node:path';

import { REPO } from './config.mjs';

const read = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));

export function spec(key) {
  const base = path.join(REPO, 'golden', 'specs', `${key.toLowerCase()}.json`);
  // A variant (GD1-sold, slice 49) lives beside the specs; its client name is its own (golden/specs.py).
  const variant = path.join(REPO, 'golden', 'variants', `${key.toLowerCase()}.json`);
  return read(fs.existsSync(base) ? base : variant);
}

export function answerKey(key) {
  return read(path.join(REPO, 'golden', 'keys', `${key.toLowerCase()}.json`));
}

export function specKeys() {
  return fs.readdirSync(path.join(REPO, 'golden', 'specs'))
    .filter((name) => /^gd.*\.json$/.test(name))
    .map((name) => name.replace(/\.json$/, '').toUpperCase())
    .sort();
}
