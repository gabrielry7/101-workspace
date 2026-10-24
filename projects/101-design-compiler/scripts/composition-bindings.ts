import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { compositions, previewPath, COMPOSITION_VERSION } from '../src/composition/registry.ts';
import { loadCompositionLab } from './load-composition-lab.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';

export async function compositionBindings() {
  const lab=await loadCompositionLab();
  return {schema_version:COMPOSITION_VERSION,runtime:'LOCAL_ASTRO_LAB_ONLY',site_plan_id:lab.content.site_plan_id,
    plan_sha256:lab.content.plan_sha256,requirements_sha256:lab.content.requirements_sha256,content_sha256:lab.content.content_sha256,
    manifest_sha256:lab.manifest_sha256,client_id:lab.client_id,project_id:lab.project_id,
    variants:compositions.map(c=>({id:c.id,operator:c.operator,pages:lab.content.pages.map(p=>({semantic_path:p.path,preview_path:previewPath(c.id,p.path),
      modules:p.modules.map(m=>({module_id:m.id,component:m.component,scope_id:m.scope_id,required:m.required,
        fact_ids:[...m.facts,...m.offerings.flatMap(o=>o.facts)].map(f=>f.id),offering_ids:m.offerings.map(o=>o.id),
        media_usage_ids:lab.media.usage.module_id===m.id&&lab.media.usage.page===p.path?[lab.media.usage.id]:[]}))}))})),
    bindings:lab.content.bindings,diagnostics:lab.content.diagnostics,exclusions:lab.content.exclusions,restrictions:lab.content.restrictions,
    media_constraints:lab.constraints,gaps:lab.gaps};
}
if(process.argv[1]?.endsWith('composition-bindings.ts')){
  const value=await compositionBindings(),body=JSON.stringify(value,null,2)+'\n',path='data/derived/composition-v1/restaurante-bindings.json';
  if(process.argv.includes('--replay')){if(await readFile(path,'utf8')!==body)throw new Error('COMPOSITION_BINDINGS_REPLAY_MISMATCH');}
  else {await mkdir('data/derived/composition-v1',{recursive:true});await writeFile(path,body);}
  console.log(`Composition bindings ${process.argv.includes('--replay')?'replayed':'exported'}: ${inputSha256(value)}`);
}
