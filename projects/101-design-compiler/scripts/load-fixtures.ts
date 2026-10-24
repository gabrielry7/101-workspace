import { readFile } from 'node:fs/promises';

export const fixtureNames = ['restaurante', 'gimnasio', 'ferreteria'] as const;
export async function loadFixture(name: typeof fixtureNames[number]): Promise<unknown> {
  return JSON.parse(await readFile(new URL(`../fixtures/v1/${name}.json`, import.meta.url), 'utf8')) as unknown;
}
