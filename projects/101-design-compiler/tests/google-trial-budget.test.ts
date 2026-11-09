import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { reserveTrialLoad } from '../tooling/bones/google-trial-budget.mjs';

test('trial reservations persist and reject an eleventh initialization', async () => {
  const path = join(await mkdtemp(join(tmpdir(), 'maps-budget-')), 'budget.json');
  for (let count = 1; count <= 10; count++) {
    const result = reserveTrialLoad(path);
    assert.equal(result.reserved, count);
    assert.equal(result.remaining, 10 - count);
  }
  assert.throws(() => reserveTrialLoad(path), /TRIAL_BUDGET_EXHAUSTED/);
  assert.equal(JSON.parse(await readFile(path, 'utf8')).reserved, 10);
});

test('malformed state or a changed limit fails closed instead of resetting spend', async () => {
  const path = join(await mkdtemp(join(tmpdir(), 'maps-budget-invalid-')), 'budget.json');
  await writeFile(path, JSON.stringify({ schema: '101-google-trial-budget-v1', limit: 10, reserved: -1 }));
  assert.throws(() => reserveTrialLoad(path), /INVALID_TRIAL_BUDGET_STATE/);
  assert.throws(() => reserveTrialLoad(path, 100), /INVALID_TRIAL_LIMIT/);
  await writeFile(path, JSON.stringify({ schema: '101-google-trial-budget-v1', limit: 9, reserved: 2 }));
  assert.throws(() => reserveTrialLoad(path), /INVALID_TRIAL_BUDGET_STATE/);
});
