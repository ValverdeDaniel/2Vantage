// One spec, both apps (Q.9 row 3; plan.md §12.7): read each golden deal back through old Vantage's API and
// 2Vantage's, and compare its plans, key values, stars and monthly totals with the spec and its answer key.
//
//   npm --prefix browser run check-loaded [-- --deals GD1,GD2] [--apps old,new]
//
// The spec's parity profile says what the old app cannot hold (values_left_out); those are not compared there.
// The monthly totals preview "the old app as an answer key" (§12.6), which is formally run before slice 7.
// Exit 1 when anything the spec says differs.

import { dealId, session } from '../shared/apps.mjs';
import { list, parseArgs } from '../shared/args.mjs';
import { answerKey, spec as loadSpec, specKeys } from '../shared/golden.mjs';

const KEY_VALUES = ['rate_ee', 'rate_es', 'rate_ec', 'rate_fam', 'plan_type', 'deductible_single', 'oop_max_single'];

const same = (a, b) => {
  const [x, y] = [Number(String(a ?? '').replace(/[$,]/g, '')), Number(String(b ?? '').replace(/[$,]/g, ''))];
  if (String(a ?? '').trim() !== '' && !Number.isNaN(x) && !Number.isNaN(y)) return x === y;
  return String(a ?? '').trim() === String(b ?? '').trim();
};

async function oldPlans(sess, spec) {
  const body = await sess.get(`/api/benefits/cases/${await dealId(sess, spec.client)}/comparison/`);
  const values = {};
  for (const row of body.rows) for (const [pid, cell] of Object.entries(row.cells || {})) (values[pid] ||= {})[row.key] = cell?.value ?? '';
  return body.plans.map((p) => ({
    line: p.line, carrier: p.carrier, name: p.plan_name,
    role: p.is_current ? 'current' : (p.renewal_of ? 'renewal' : 'alternate'),
    starred: p.is_shortlisted, values: values[p.id] || {}, monthly: body.computed?.monthly_totals?.[p.id] ?? null,
  }));
}

async function newPlans(sess, spec) {
  const id = await dealId(sess, spec.client);
  const out = [];
  for (const line of spec.lines) {
    const body = await sess.get(`/api/deals/${id}/plans/?line=${line}`);
    for (const p of body.plans) {
      out.push({ line, carrier: p.carrier, name: p.name, role: p.role, starred: p.starred, values: p.values, monthly: p.premium?.monthly ?? null });
    }
  }
  return out;
}

function compare(app, spec, key, plans) {
  const wrong = [];
  const leftOut = app === 'old' ? new Set(Object.keys(spec.parity.values_left_out || {})) : new Set();
  const taken = new Set();
  for (const plan of spec.plans) {
    const hit = plans.find((p, i) => !taken.has(i) && p.line === plan.line && p.carrier === plan.carrier
      && p.name === plan.name && p.role === plan.role);
    if (!hit) {
      wrong.push(`${plan.ref}: not found`);
      continue;
    }
    taken.add(plans.indexOf(hit));
    const keys = app === 'old' ? Object.keys(plan.values) : KEY_VALUES.filter((k) => k in plan.values);
    for (const k of keys.filter((name) => !leftOut.has(name))) {
      if (!same(hit.values[k], plan.values[k])) wrong.push(`${plan.ref}.${k}: ${hit.values[k]} != ${plan.values[k]}`);
    }
    if (Boolean(hit.starred) !== spec.starred.includes(plan.ref)) wrong.push(`${plan.ref}: starred ${hit.starred}`);
    const expected = key.plans[plan.ref]?.monthly;
    const excused = app === 'old' && plan.ref in (spec.parity.figures_left_out || {});
    if (expected !== undefined && !excused && !same(hit.monthly, expected)) {
      wrong.push(`${plan.ref}: monthly ${hit.monthly} != key ${expected}`);
    }
  }
  if (plans.length !== spec.plans.length) wrong.push(`${plans.length} plans, the spec has ${spec.plans.length}`);
  return wrong;
}

const args = parseArgs();
const keys = args.deals ? list(args.deals).map((k) => k.toUpperCase()) : specKeys();
const apps = args.apps ? list(args.apps) : ['old', 'new'];
const sessions = Object.fromEntries(await Promise.all(apps.map(async (app) => [app, await session(app)])));
let failed = 0;
for (const key of keys) {
  const spec = loadSpec(key);
  const figures = answerKey(key);
  for (const app of apps) {
    const plans = app === 'old' ? await oldPlans(sessions.old, spec) : await newPlans(sessions.new, spec);
    const wrong = compare(app, spec, figures, plans);
    failed += wrong.length ? 1 : 0;
    console.log(`${wrong.length ? 'FAIL' : 'PASS'}  ${key} in ${app === 'old' ? 'old Vantage' : '2Vantage'}: ${plans.length} plans`
      + `${wrong.length ? `\n      ${wrong.join('\n      ')}` : ', values, stars and monthly totals as the spec and key say'}`);
  }
  const left = (spec.parity.left_out || []).map((item) => item.what);
  if (left.length) console.log(`      left out of old Vantage by the profile: ${left.join('; ')}`);
  for (const [ref, why] of Object.entries(spec.parity.figures_left_out || {})) console.log(`      ${ref}'s figure is not compared in old Vantage: ${why}`);
}
process.exit(failed ? 1 : 0);
