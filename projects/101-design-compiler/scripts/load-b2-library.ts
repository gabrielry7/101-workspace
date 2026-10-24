import {readFile} from 'node:fs/promises';
import {BusinessInputV1,BusinessProfileV1,CapabilityProfileV1,SitePlanV1} from '../src/contracts/v1/schemas.ts';
import {FunctionalDiagnosticV1} from '../src/requirements/contracts.ts';
import {verifyMediaLibrary,libraryData,evaluateLibraryUsage} from '../src/media/library.ts';
export async function loadB2Library(options:{evaluation_time?:string}={}){
 const base=JSON.parse(await readFile('data/derived/requirements-v1/restaurante.json','utf8')),p=base.planner;
 const bundle={input:BusinessInputV1.parse(p.input),profile:BusinessProfileV1.parse(p.profile),capabilities:CapabilityProfileV1.parse(p.capabilities),plan:SitePlanV1.parse(p.plan)};
 const raw=JSON.parse(await readFile('data/media/library-v1/usda-pilot.json','utf8'));
 const verification=await verifyMediaLibrary(raw,bundle,p.requirements);
 if(!verification.success)throw Error(`B2_LIBRARY_NOT_VERIFIED:${verification.codes.join(',')}`);
 const library=libraryData(verification.handle),evaluated_at=options.evaluation_time??new Date().toISOString();
 const decisions=library.manifest.usages.map(u=>evaluateLibraryUsage(verification.handle,u,evaluated_at));
 if(decisions.some(d=>d.status!=='ALLOWED'))throw Error(`B2_LIBRARY_USE_NOT_CURRENTLY_ALLOWED:${decisions.flatMap(d=>d.codes).join(',')}`);
 return {handle:verification.handle,library,bundle,requirements:p.requirements,diagnostic:FunctionalDiagnosticV1.parse(base.diagnostic),evaluated_at};
}
