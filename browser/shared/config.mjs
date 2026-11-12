// Where the two apps run, who signs in, and where output goes (plan.md §12.7). Every value has an env override.
// The users are synthetic: old Vantage's comes from tools/parity/old_loader.py, 2Vantage's is a local superuser.

import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const env = process.env;

export const BROWSER_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const REPO = path.resolve(BROWSER_DIR, '..');

export const OLD = {
  name: 'old',
  base: env.LOOK_OLD_BASE || 'http://localhost:4002',
  api: env.LOOK_OLD_API || 'http://localhost:8005',
  user: env.PARITY_USER || 'parity-admin',
  password: env.PARITY_PASSWORD || 'parity-only-pw',
};

export const NEW = {
  name: 'new',
  base: env.LOOK_NEW_BASE || 'http://localhost:4001',
  user: env.LOOK_NEW_USER || 'golden-admin',
  password: env.LOOK_NEW_PASSWORD || 'golden-admin-pw',
};

// Output lives outside the OneDrive-synced repository (§3.4, Q.2).
export const OUT = env.LOOK_OUT || path.join(env.LOCALAPPDATA || os.homedir(), '2vantage-look');

// The installed Chrome, as the old e2e checks use it (devtools/e2e/_lib.mjs at 891f1b3); CHROME_PATH overrides.
export const CHROME_PATH = env.CHROME_PATH || '';

// The clock both apps' pages see, so "today" and relative dates draw the same (Q.5 determinism).
export const FIXED_NOW = env.LOOK_NOW || '2026-11-11T14:00:00-05:00';

export const WIDTHS = { default: [1440], workspace: [1280, 1440, 1920] };
export const HEIGHT = 900;
