import test from 'node:test';
import assert from 'node:assert/strict';
import { loadMediaPilot } from '../scripts/load-media-pilot.ts';
import { buildMediaManifest } from '../src/media/plan.ts';
import { verifyPackageFiles } from '../src/media/package.ts';
import { rightsGate, evaluateSuitability } from '../src/media/gate.ts';

test('actual source documents, original JPEG and browser evidence validate an authorized pilot', async () => {
  const p = await loadMediaPilot();
  assert.equal(p.output.brief.closure, 'AUTHORIZED_PILOT_PACKAGE_WITH_GAPS');
  assert.equal(p.output.manifest.decisions[0]?.status, 'ALLOWED');
  assert.equal(p.inventory.assets[0]?.data_mode, 'REAL');
  assert.equal(p.output.brief.gaps.length, 1); assert.equal(p.output.brief.gaps[0]?.need.role, 'DOCUMENTARY');
  assert.ok((await verifyPackageFiles(p.context.package_proof, p.output.manifest)).success);
});
test('REAL / VERIFIED claims and even a valid grant cannot close without checked package evidence', async () => {
  const p = await loadMediaPilot({ unsealed: true });
  assert.equal(p.output.manifest.decisions[0]?.status, 'ALLOWED');
  assert.equal(p.output.brief.closure, 'PENDING_AUTHORIZED_MEDIA_PACKAGE');
});
test('changed original, authorization document, render receipt or project fails byte evidence verification', async () => {
  const p = await loadMediaPilot();
  for (const mutate of [
    (proof: NonNullable<typeof p.context.package_proof>) => { proof.files[0]!.sha256 = 'a'.repeat(64); },
    (proof: NonNullable<typeof p.context.package_proof>) => { proof.documents[0]!.sha256 = 'a'.repeat(64); },
    (proof: NonNullable<typeof p.context.package_proof>) => { proof.render.receipt_sha256 = 'a'.repeat(64); },
    (proof: NonNullable<typeof p.context.package_proof>) => { proof.project_id = 'other-project'; },
  ]) {
    const proof = structuredClone(p.context.package_proof!); mutate(proof);
    assert.equal((await verifyPackageFiles(proof, p.output.manifest)).success, false);
  }
});
test('attribution, contextual notice and no-endorsement condition are enforced, not erased', async () => {
  const p = await loadMediaPilot(); const a = p.inventory.assets[0]!, g = p.inventory.grants[0]!;
  assert.ok(a.restrictions.includes('NO_PROVIDER_ENDORSEMENT')); assert.ok(g.restrictions.includes('NO_PROVIDER_ENDORSEMENT'));
  for (const mutation of ['credit', 'notice', 'endorsement'] as const) {
    const usage = structuredClone(p.inventory.usages[0]!);
    if (mutation === 'credit') usage.attribution_text = null;
    if (mutation === 'notice') usage.context_notices = [];
    if (mutation === 'endorsement') usage.endorsement_claimed = true;
    assert.equal(rightsGate(a, g, usage, [a], p.context.evaluated_at).status, 'BLOCKED');
  }
});
test('real peppers do not fill the documentary offering gap or authorize another client, transformation or AI', async () => {
  const p = await loadMediaPilot(); const a = p.inventory.assets[0]!, g = p.inventory.grants[0]!;
  const usage = structuredClone(p.inventory.usages[0]!);
  usage.role = 'DOCUMENTARY'; usage.representation = 'BUSINESS_EVIDENCE'; usage.subject_ids = ['offering-1'];
  assert.ok(evaluateSuitability(a, usage, p.context.evaluated_at).includes('MISLEADING_BUSINESS_REPRESENTATION'));
  for (const mutation of ['client', 'crop', 'ai', 'automation'] as const) {
    const u = structuredClone(p.inventory.usages[0]!);
    if (mutation === 'client') u.client_id = 'another-client';
    if (mutation === 'crop') u.transformations = ['CROP'];
    if (mutation === 'ai') u.ai_operations = ['vision'];
    if (mutation === 'automation') u.automated_access = ['download'];
    assert.equal(rightsGate(a, g, u, [a], p.context.evaluated_at).status, 'BLOCKED');
  }
});
test('false closed brief and changed subject role do not survive consumer recomputation', async () => {
  const p = await loadMediaPilot(); const i = structuredClone(p.inventory);
  i.usages[0]!.role = 'DOCUMENTARY'; i.usages[0]!.representation = 'BUSINESS_EVIDENCE';
  const output = buildMediaManifest(p.bundle, p.requirements, i, p.context);
  assert.equal(output.brief.closure, 'PENDING_AUTHORIZED_MEDIA_PACKAGE');
  assert.equal(output.manifest.decisions[0]?.status, 'BLOCKED');
});
