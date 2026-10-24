import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {projectContent} from '../composition/content.ts';
import {ContextualDesignPlanV2,ContextualPresentationV1} from './contextual-contracts.ts';
import {humanReviewCatalog} from '../requirements/review-catalog.ts';
import type {ContextualDesignPlan} from './contextual-contracts.ts';
import type {FixtureBundle} from '../contracts/v1/schemas.ts';
import type {SiteRequirements} from '../planner/contracts.ts';
// Versioned expansion of the local shared registry, not @101/site-runtime.
export const contextualOperators={
 Top:{purpose:'horizontal navigation',mobile:'wrapped links'},Rail:{purpose:'sticky navigation rail',mobile:'disclosure navigation'},Index:{purpose:'numbered navigation',mobile:'numbered wrapped index'},
 Split:{purpose:'text and natural-ratio image side by side',mobile:'title, copy, image'},Monument:{purpose:'large centered typography then image',mobile:'centered measured title, image'},
 Diptych:{purpose:'two unequal fields with aligned baselines',mobile:'compact title, natural image, copy'},Stage:{purpose:'framed media then editorial copy',mobile:'paired title and copy above a framed natural image'},
 Grid:{purpose:'equal collection columns',mobile:'Stack or Compact or Sequence'},Rows:{purpose:'image/text rows',mobile:'Stack or Compact or Sequence'},Mosaic:{purpose:'staggered columns without cropping',mobile:'Stack or Compact or Sequence'},
} as const;
export async function loadContextualScenario(root=process.cwd()){
 const scenario=JSON.parse(await readFile(resolve(root,'fixtures/corrections/b3/la-mesa.json'),'utf8'));
 const p=scenario.planner;const content=projectContent({input:p.input,profile:p.profile,capabilities:p.capabilities,plan:p.plan} as FixtureBundle,p.requirements as SiteRequirements);
 if(scenario.input.data_mode!=='SYNTHETIC_FIXTURE'||inputSha256(scenario.input)!==inputSha256(p.input)||inputSha256(content)!==inputSha256(scenario.content))throw Error('B3_CONTENT_CONTEXT_CHANGED');
 return {...scenario,content};
}
export function structuralSignature(d:Pick<ContextualDesignPlan,'recipe'>){const r=d.recipe;return {desktop:[r.navigation,r.hero,r.collection,r.narrative,r.visit,r.proportion,r.measure],mobile:[r.navigation==='Rail'?'Disclosure':r.navigation,r.hero,r.mobile_collection,r.narrative,r.visit]};}
export function validateContextualPresentation(value:unknown,s:any){
 const p=ContextualPresentationV1.safeParse(value);if(!p.success)throw Error('B3_PRESENTATION_SCHEMA_INVALID');const v=p.data,modules=s.content.pages.flatMap((p:any)=>p.modules),ids=modules.map((m:any)=>m.id).sort(),offers=modules.flatMap((m:any)=>m.offerings).map((o:any)=>o.id).sort();
 const same=(a:unknown,b:unknown)=>inputSha256(a)===inputSha256(b);
 if(!same(Object.keys(v.module_headings).sort(),ids)||!same(Object.keys(v.anchors).sort(),ids)||new Set(Object.values(v.anchors)).size!==ids.length||!same([...v.offering_order].sort(),offers)||!same(Object.keys(v.offering_media).sort(),offers))throw Error('B3_PRESENTATION_BINDINGS_INVALID');
 // B3 slot convention binds an offering to b3-need:<offering id>. The media
 // review separately pins that need to inspected bytes; this is not a licence.
 if(offers.some((id:string)=>v.offering_media[id]!==id))throw Error('B3_OFFERING_MEDIA_MISMATCH');
 if(Object.values(v.preview_catalog_references).some(id=>!humanReviewCatalog.features.some(f=>f.id===id)))throw Error('B3_PREVIEW_CATALOG_REFERENCE_INVALID');
 return v;
}
export function structuralDistance(a:Pick<ContextualDesignPlan,'recipe'>,b:Pick<ContextualDesignPlan,'recipe'>){const x=structuralSignature(a),y=structuralSignature(b);return {desktop:x.desktop.filter((v,i)=>v!==y.desktop[i]).length,mobile:x.mobile.filter((v,i)=>v!==y.mobile[i]).length};}
export function validateContextualPlan(value:unknown,scenario:any,context_sha256:string,media_sha256:string){
 const parsed=ContextualDesignPlanV2.safeParse(value);if(!parsed.success)return {success:false as const,codes:['B3_PLAN_SCHEMA_INVALID']};const d=parsed.data,codes:string[]=[];
 const modules=scenario.content.pages.flatMap((p:any)=>p.modules).map((m:any)=>m.id).sort();
 if(inputSha256([...d.module_refs].sort())!==inputSha256(modules))codes.push('B3_MODULE_COVERAGE_MISMATCH');
 const bound=[d.sections.identity,d.sections.narrative,d.sections.collection,...d.sections.information];
 if(inputSha256([...bound].sort())!==inputSha256(modules))codes.push('B3_SECTION_BINDING_MISMATCH');
 const projected=scenario.content.pages.flatMap((p:any)=>p.modules),find=(id:string)=>projected.find((m:any)=>m.id===id);
 if(find(d.sections.identity)?.component!=='Identity'||find(d.sections.collection)?.component!=='OfferingCollection'||find(d.sections.narrative)?.component!=='FactCollection')codes.push('B3_COMPONENT_SIGNATURE_MISMATCH');
 if(d.context_sha256!==context_sha256||d.plan_sha256!==scenario.content.plan_sha256||d.content_sha256!==scenario.content.content_sha256||d.media_sha256!==media_sha256)codes.push('B3_CONTEXT_MISMATCH');
 if(d.route!==`/b3/${d.id}/`)codes.push('B3_ROUTE_MISMATCH');
 return {success:!codes.length,codes};
}
