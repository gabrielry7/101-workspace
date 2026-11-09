import { existsSync, readFileSync, writeFileSync, renameSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

export function reserveTrialLoad(path, limit = 10) {
  if (!Number.isInteger(limit) || limit < 1 || limit > 10) throw Error('INVALID_TRIAL_LIMIT');
  const state = existsSync(path) ? JSON.parse(readFileSync(path, 'utf8'))
    : { schema: '101-google-trial-budget-v1', reserved: 0, limit };
  if (state.schema !== '101-google-trial-budget-v1' || state.limit !== limit
    || !Number.isInteger(state.reserved) || state.reserved < 0 || state.reserved > limit) {
    throw Error('INVALID_TRIAL_BUDGET_STATE');
  }
  if (state.reserved >= limit) throw Error('TRIAL_BUDGET_EXHAUSTED');
  state.reserved++;
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = path + '.tmp';
  writeFileSync(temporary, JSON.stringify(state, null, 2) + '\n', { mode: 0o600 });
  renameSync(temporary, path);
  return { reserved: state.reserved, limit, remaining: limit - state.reserved,
    conservative_list_price_usd: state.reserved * 7 / 1000, authorized_budget_usd: 1 };
}
