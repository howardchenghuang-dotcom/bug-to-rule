// Repo-wide rules. Each one is a bug we already paid for, turned into a check.
// Copy to test/repo-rules.test.mjs and keep only the rules that match a real
// incident in your project. Exceptions go in an allowlist with a reason;
// never loosen a pattern to make existing code pass.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname;
const CODE = ['lib', 'src', 'scripts', 'server.mjs'];   // edit to your layout

function walk(p, out = []) {
  const s = statSync(p, { throwIfNoEntry: false });
  if (!s) return out;
  if (s.isFile()) {
    if (/\.(mjs|js|ts|sh)$/.test(p)) out.push(p);
    return out;
  }
  for (const n of readdirSync(p)) if (n !== 'node_modules') walk(join(p, n), out);
  return out;
}
const codeFiles = () => CODE.flatMap((d) => walk(join(ROOT, d)));
const rel = (f) => relative(ROOT, f);

function hits(re, files) {
  const out = [];
  for (const f of files) {
    readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
      const t = line.trim();
      if (t.startsWith('//') || t.startsWith('*') || t.startsWith('#')) return;
      if (re.test(line)) out.push(`${rel(f)}:${i + 1}: ${t.slice(0, 120)}`);
    });
  }
  return out;
}

// If the walk breaks, every rule below passes silently.
test('the scan actually sees code', () => {
  const files = codeFiles().map(rel);
  assert.ok(files.length > 0, 'no source files found: check CODE');
  // assert.ok(files.includes('lib/billing.mjs'));   // name two files you know exist
});

// Example: a paid API was called outside the module that tracks cost, so the
// budget check never saw it (YYYY-MM-DD). Each host may appear only in its home.
const API_HOME = {
  'api.stripe.com': ['lib/stripe.mjs'],
  // 'api.example-video.com': ['lib/video-provider.mjs'],
};

test('paid APIs are called only from their own module', () => {
  const bad = [];
  for (const [host, homes] of Object.entries(API_HOME)) {
    for (const h of hits(new RegExp(host.replace(/\./g, '\\.')), codeFiles())) {
      if (!homes.some((home) => h.startsWith(home + ':'))) bad.push(h);
    }
  }
  assert.deepEqual(bad, [], 'move the call into its module, where cost is recorded');
});

// Example: `npm test | tail` reports the exit code of tail, so a red suite
// looked green in the deploy script (YYYY-MM-DD).
test('scripts do not pipe test runs without pipefail', () => {
  const files = walk(join(ROOT, 'scripts'));
  const bad = hits(/(npm (run )?test|node --test|pytest)[^\n]*\|(?!\|)/, files)
    .filter((h) => !readFileSync(join(ROOT, h.split(':')[0]), 'utf8').includes('pipefail'));
  assert.deepEqual(bad, []);
});

// Coverage example: every provider in the price table must have a cost entry,
// derived from the table itself so a new provider cannot be skipped.
// import { PRICE_TABLE } from '../lib/prices.mjs';
// import { COST } from '../lib/costs.mjs';
// test('every priced provider has a cost', () => {
//   for (const p of Object.keys(PRICE_TABLE)) assert.ok(COST[p], `${p}: no cost entry`);
// });
