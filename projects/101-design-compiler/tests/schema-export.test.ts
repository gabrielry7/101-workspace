import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { z } from 'zod';
import { contracts } from '../src/contracts/v1/schemas.ts';
import { CategoryRecordV1, MappingRegistryV1, TaxonomyObservationV1, ActivityRelationshipV1, CandidateCapabilityV1 } from '../src/taxonomy/contracts.ts';
import { UpstreamEnvelopeV1 } from '../src/upstream/v1/protocol.ts';
import { CapabilitySpecV1, CapabilityRegistryV1, SiteRequirementsV1 } from '../src/planner/contracts.ts';
import { mediaContracts } from '../src/media/contracts.ts';
import { designContracts, designContractsV1_1 } from '../src/design/contracts.ts';
import { lockContracts } from '../src/lock/contracts.ts';
import { auditContracts } from '../src/audit/contracts.ts';

for (const [name, schema] of Object.entries(contracts)) {
  test(`${name}: portable JSON Schema stays synchronized with source`, async () => {
    const exported = JSON.parse(await readFile(new URL(`../contracts/v1/${name}.schema.json`, import.meta.url), 'utf8')) as Record<string, unknown>;
    const { $id, title, description, ...structural } = exported;
    assert.equal($id, `urn:unocerouno:contracts:${name}:1.0.0`);
    assert.equal(title, name);
    assert.equal(typeof description, 'string');
    assert.deepEqual(structural, z.toJSONSchema(schema, { target: 'draft-2020-12' }));
  });
}

for (const [group, schemas] of Object.entries({
  'taxonomy/v1': { CategoryRecordV1, MappingRegistryV1, TaxonomyObservationV1, ActivityRelationshipV1, CandidateCapabilityV1 },
  'upstream/v1': { UpstreamEnvelopeV1 },
  'planner/v1': { CapabilitySpecV1, CapabilityRegistryV1, SiteRequirementsV1 },
  'media/v1': mediaContracts,
  'design/v1': designContracts,
  'design/v1.1': designContractsV1_1,
  'audit/v1': auditContracts,
  'lock/v1': lockContracts,
})) {
  for (const [name, schema] of Object.entries(schemas)) {
    test(`${name}: schema export is synchronized and separately versioned`, async () => {
      const exported = JSON.parse(await readFile(new URL(`../contracts/${group}/${name}.schema.json`, import.meta.url), 'utf8')) as Record<string, unknown>;
      const { $id, title, description, ...structural } = exported;
      assert.equal($id, `urn:unocerouno:contracts:${name}:${group === 'design/v1.1' ? '1.1.0' : '1.0.0'}`);
      assert.equal(title, name); assert.equal(typeof description, 'string');
      assert.deepEqual(structural, z.toJSONSchema(schema, { target: 'draft-2020-12' }));
    });
  }
}
