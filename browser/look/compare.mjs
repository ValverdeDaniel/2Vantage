// Comparing one screen state between the apps (Q.5): pixels, class order and computed style. Pure over the
// captures: files and measurements in, a verdict per check out.

import fs from 'node:fs';

import pixelmatch from 'pixelmatch';
import { PNG } from 'pngjs';

export const THRESHOLD = 0.1; // pixelmatch's colour threshold
export const SAME_RATIO = 0.0002; // "same": at most 0.02% of pixels differ
export const BOX_TOLERANCE = 1; // px

function padded(png, width, height) {
  if (png.width === width && png.height === height) return png;
  const out = new PNG({ width, height, fill: true });
  out.data.fill(0); // transparent: everything outside the smaller capture counts as different
  PNG.bitblt(png, out, 0, 0, png.width, png.height, 0, 0);
  return out;
}

export function pixels(oldFile, newFile, diffFile) {
  const a = PNG.sync.read(fs.readFileSync(oldFile));
  const b = PNG.sync.read(fs.readFileSync(newFile));
  const width = Math.max(a.width, b.width);
  const height = Math.max(a.height, b.height);
  const diff = new PNG({ width, height });
  const count = pixelmatch(padded(a, width, height).data, padded(b, width, height).data, diff.data, width, height, {
    threshold: THRESHOLD,
  });
  fs.writeFileSync(diffFile, PNG.sync.write(diff));
  const ratio = count / (width * height);
  return {
    same: ratio <= SAME_RATIO,
    different_pixels: count,
    ratio: Number(ratio.toFixed(6)),
    old_size: [a.width, a.height],
    new_size: [b.width, b.height],
  };
}

export function classes(oldList, newList) {
  let first = -1;
  const length = Math.max(oldList.length, newList.length);
  for (let i = 0; i < length; i += 1) {
    if (oldList[i] !== newList[i]) {
      first = i;
      break;
    }
  }
  const newSet = new Set(newList);
  const oldSet = new Set(oldList);
  return {
    same: first === -1,
    old_count: oldList.length,
    new_count: newList.length,
    first_difference: first === -1 ? null : { index: first, old: oldList[first] ?? null, new: newList[first] ?? null },
    missing_in_new: [...oldSet].filter((name) => !newSet.has(name)).slice(0, 40),
    extra_in_new: [...newSet].filter((name) => !oldSet.has(name)).slice(0, 40),
  };
}

const px = (value) => (/^-?[\d.]+px$/.test(value) ? parseFloat(value) : null);

function close(a, b) {
  const [x, y] = [px(a), px(b)];
  if (x !== null && y !== null) return Math.abs(x - y) <= BOX_TOLERANCE;
  return a === b;
}

export function style(oldStyles, newStyles) {
  const out = {};
  let same = true;
  for (const selector of Object.keys(oldStyles)) {
    const a = oldStyles[selector];
    const b = newStyles[selector];
    if (!a && !b) {
      out[selector] = 'in neither';
      continue;
    }
    if (!a || !b) {
      out[selector] = a ? 'missing in new' : 'missing in old';
      same = false;
      continue;
    }
    const diffs = {};
    for (const [prop, value] of Object.entries(a.style)) {
      if (!close(value, b.style[prop])) diffs[prop] = [value, b.style[prop]];
    }
    for (const side of ['x', 'y', 'width', 'height']) {
      if (Math.abs(a.box[side] - b.box[side]) > BOX_TOLERANCE) diffs[`box.${side}`] = [a.box[side], b.box[side]];
    }
    out[selector] = Object.keys(diffs).length ? diffs : 'same';
    if (Object.keys(diffs).length) same = false;
  }
  return { same, selectors: out };
}
