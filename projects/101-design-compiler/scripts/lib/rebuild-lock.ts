import { readFile,writeFile,mkdir,copyFile,access } from 'node:fs/promises';
import { resolve,relative,dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { performance } from 'node:perf_hooks';
import http from 'node:http';
import https from 'node:https';
import { syncBuiltinESMExports } from 'node:module';
import os from 'node:os';
import { validateLock } from '../../src/lock/validate.ts';
import { inputSha256 } from '../../src/upstream/v1/protocol.ts';
import type { DesignLock } from '../../src/lock/contracts.ts';
import { verifyPackageFiles } from '../../src/media/package.ts';
import { fingerprint,installedFingerprint,browserFingerprint,fontFingerprint,sha,within,sourceGraph } from './lock-files.ts';
export const REBUILD_ENTRIES=['src/components/composition/DesignComposition.astro','src/lock/validate.ts','src/lock/rollback.ts','scripts/audit-h8.ts','scripts/lib/rebuild-lock.ts','scripts/rebuild-h8.ts','src/audit/evaluate.ts','src/composition/observe.ts','src/audit/raster.ts','src/audit/png.ts','scripts/lib/local-browser.ts'];
export async function materializeLockSources(lock:DesignLock,runId:string,root=process.cwd()){
 if(!/^[a-z0-9-]+$/.test(runId))throw Error('INVALID_SOURCE_RESTORE_ID');const target=within(root,`.tools/h8-source/${runId}`);if(await access(target).then(()=>true,()=>false))throw Error('SOURCE_RESTORE_ALREADY_EXISTS');
 for(const source of lock.sources){const text=(await readFile(within(root,`${lock.source_snapshot_root}/${source.path}.txt`),'utf8')).replace(/\r\n/g,'\n');if(sha(text)!==source.sha256)throw Error(`LOCK_SOURCE_ARCHIVE_MISMATCH:${source.path}`);const path=within(target,source.path);await mkdir(dirname(path),{recursive:true});await writeFile(path,text);}
 return target;
}
export async function verifyLockFiles(lock:DesignLock,root=process.cwd(),sourceRoot=root){
 const checked=validateLock(lock);if(!checked.success)throw Error(`LOCK_INVALID:${checked.codes}`);
 const executor=lock.sources.find(s=>s.path==='scripts/lib/rebuild-lock.ts');if(!executor||sha((await readFile(fileURLToPath(import.meta.url),'utf8')).replace(/\r\n/g,'\n'))!==executor.sha256)throw Error('LOCK_EXECUTOR_VERSION_MISMATCH');
 for(const source of lock.sources){const current=await fingerprint(sourceRoot,source.path,source.normalization);if(current.sha256!==source.sha256)throw Error(`LOCK_SOURCE_MISMATCH:${source.path}`);}
 const graph=await sourceGraph(sourceRoot,REBUILD_ENTRIES);if(JSON.stringify(graph.paths)!==JSON.stringify(lock.sources.map(s=>s.path)))throw Error('LOCK_SOURCE_GRAPH_MISMATCH');
 if(process.version!==lock.toolchain.node_version||process.platform!==lock.toolchain.platform||process.arch!==lock.toolchain.arch||sha(await readFile(process.execPath))!==lock.toolchain.node_sha256)throw Error('LOCK_NODE_MISMATCH');
 for(const f of lock.toolchain.lockfiles){if((await fingerprint(root,f.path,f.normalization)).sha256!==f.sha256)throw Error(`LOCK_TOOLCHAIN_MISMATCH:${f.path}`);}
 const installed=await installedFingerprint(root);if(JSON.stringify(installed)!==JSON.stringify(lock.toolchain.installed_dependencies))throw Error('LOCK_INSTALLED_DEPENDENCIES_MISMATCH');
 const browser=await browserFingerprint();if(browser.version!==lock.toolchain.browser_version||JSON.stringify(browser.files)!==JSON.stringify(lock.toolchain.browser_files))throw Error('LOCK_BROWSER_MISMATCH');
 if(os.release()!==lock.environment.os_release||os.version()!==lock.environment.os_version||JSON.stringify(await fontFingerprint())!==JSON.stringify(lock.environment.font_files))throw Error('LOCK_OS_OR_FONT_MISMATCH');
 for(const file of lock.files){const bytes=await readFile(within(root,file.stored_path));if(bytes.length!==file.bytes||sha(bytes)!==file.sha256)throw Error(`LOCK_STORED_FILE_MISMATCH:${file.path}`);}
 for(const file of [lock.audit_state.source,lock.audit_state.source.lock_file,...lock.audit_state.evidence]){const bytes=await readFile(within(root,file.stored_path));if(bytes.length!==file.bytes||sha(bytes)!==file.sha256)throw Error(`LOCK_AUDIT_FILE_MISMATCH:${file.path}`);}
 const auditSource=JSON.parse(await readFile(within(root,lock.audit_state.source.stored_path),'utf8')),group=auditSource.originals.find((g:any)=>g.label===lock.audit_state.source.group_label);
 if(auditSource.created_at!==lock.audit_state.source.created_at||!auditSource.locks.some((l:any)=>l.id===group?.lock_id&&l.lock_sha256===lock.audit_state.source.lock_sha256)||inputSha256(group?.views)!==inputSha256(lock.audit_state.entries))throw Error('LOCK_AUDIT_SOURCE_REPORT_MISMATCH');
 const baseline=JSON.parse(await readFile(within(root,lock.audit_state.source.lock_file.stored_path),'utf8'));const {lock_sha256:baselineHash,...baselinePayload}=baseline;
 if(inputSha256(baselinePayload)!==baselineHash||baselineHash!==lock.audit_state.source.lock_sha256||inputSha256(baseline.resolved_plan)!==inputSha256(lock.resolved_plan)||inputSha256(baseline.lab)!==inputSha256(lock.lab)||lock.audit_state.renderer_sources.some(f=>!baseline.sources.some((s:any)=>s.path===f.path&&s.sha256===f.sha256)))throw Error('LOCK_AUDIT_BASELINE_SNAPSHOT_MISMATCH');
 const auditGraph=await sourceGraph(sourceRoot,['src/components/composition/DesignComposition.astro','src/audit/evaluate.ts']);if(JSON.stringify(auditGraph.paths)!==JSON.stringify(lock.audit_state.renderer_sources.map(f=>f.path)))throw Error('LOCK_AUDIT_GRAPH_MISMATCH');
 if(lock.media.manifest.package_proof){const packageCheck=await verifyPackageFiles(lock.media.manifest.package_proof,lock.media.manifest,within(root,lock.media_snapshot_root));if(!packageCheck.success)throw Error(`LOCK_MEDIA_PACKAGE_MISMATCH:${packageCheck.codes}`);}
 return {graph,validated:true};
}
export async function rebuildLock(lock:DesignLock,options:{run_id:string;root?:string;source_root?:string;sentinel_import?:boolean;allow_seeded_experiment?:boolean}){
 if(!/^[a-z0-9-]+$/.test(options.run_id))throw Error('INVALID_REBUILD_RUN_ID');const root=resolve(options.root??process.cwd()),sourceRoot=resolve(options.source_root??root);const started=performance.now();
 if(lock.purpose==='SEEDED_COMPONENT_REGRESSION'&&!options.allow_seeded_experiment)throw Error('SEEDED_LOCK_REQUIRES_EXPERIMENT');
 const verified=await verifyLockFiles(lock,root,sourceRoot);const runRoot=within(root,`.tools/h8-rebuild/${options.run_id}`);
 if(await access(runRoot).then(()=>true,()=>false))throw Error('REBUILD_OUTPUT_ALREADY_EXISTS');
 await mkdir(`${runRoot}/src/pages`,{recursive:true});await mkdir(`${runRoot}/public`,{recursive:true});
 for(const file of lock.files.filter(f=>f.role==='AUTHORIZED_MEDIA')){if(!file.path.startsWith('public/'))throw Error('LOCK_MEDIA_PATH_INVALID');const target=within(runRoot,file.path);await mkdir(dirname(target),{recursive:true});await copyFile(within(root,file.stored_path),target);}
 const componentImport=relative(`${runRoot}/src/pages`,within(sourceRoot,'src/components/composition/DesignComposition.astro')).replaceAll('\\','/');const forbiddenImport=relative(`${runRoot}/src/pages`,within(root,'src/design/search.ts')).replaceAll('\\','/');
 const snapshot={lab:lock.lab,resolved_plan:lock.resolved_plan,mount:lock.mount};
 const wrapper=`---\nimport DesignComposition from ${JSON.stringify(componentImport)};\n${options.sentinel_import?`import {searchDesigns} from ${JSON.stringify(forbiddenImport)};\nconsole.log(searchDesigns);\n`:''}export function getStaticPaths(){const snapshot=${JSON.stringify(snapshot).replaceAll('<','\\u003c')};return snapshot.resolved_plan.pages.map(p=>({params:{path:snapshot.mount.kind+'/'+snapshot.mount.id+(p.path==='/'?'':p.path)},props:{page:p.path,lab:snapshot.lab,design:snapshot.resolved_plan,mount:snapshot.mount}}));}\nconst {page,lab,design,mount}=Astro.props;\n---\n<DesignComposition lab={lab} design={design} page={page} mount={mount.kind} mountId={mount.id}/>\n`;
 await writeFile(`${runRoot}/src/pages/[...path].astro`,wrapper);const modules=new Set<string>();const forbiddenAttempts:string[]=[];
 const forbidden=(id:string)=>/\/src\/design\/search\.ts(?:$|\?)|\/scripts\/(?:load-|record-|reserve-)|\/src\/planner\/plan\.ts(?:$|\?)/.test(id.replaceAll('\\','/'));
 process.env['ASTRO_TELEMETRY_DISABLED']='1';const build=await import('astro').then(m=>m.build);const previousFetch=globalThis.fetch;let networkAttempts=0;const denyNetwork=()=>{networkAttempts++;throw Error('H8_BUILD_NETWORK_FORBIDDEN');};globalThis.fetch=(async()=>denyNetwork()) as typeof fetch;
 const requests={http_request:http.request,http_get:http.get,https_request:https.request,https_get:https.get};http.request=denyNetwork as typeof http.request;http.get=denyNetwork as typeof http.get;https.request=denyNetwork as typeof https.request;https.get=denyNetwork as typeof https.get;syncBuiltinESMExports();
 try{await build({root:root+'/',configFile:false,srcDir:runRoot+'/src/',publicDir:runRoot+'/public/',outDir:runRoot+'/dist/',cacheDir:runRoot+'/cache/',output:'static',logLevel:options.sentinel_import?'silent':'info',
  vite:{plugins:[{name:'h8-no-generative-imports',enforce:'pre',resolveId(source){if(forbidden(source)){forbiddenAttempts.push(source);throw Error(`H8_FORBIDDEN_IMPORT:${source}`);}return null;},load(id){if(forbidden(id)){forbiddenAttempts.push(id);throw Error(`H8_FORBIDDEN_IMPORT:${id}`);}modules.add(id.replaceAll(root.replaceAll('\\','/'),'<WORKSPACE>'));return null;}}]}} as Parameters<typeof build>[0]);}
 finally{globalThis.fetch=previousFetch;http.request=requests.http_request;http.get=requests.http_get;https.request=requests.https_request;https.get=requests.https_get;syncBuiltinESMExports();}
 if(networkAttempts||forbiddenAttempts.length)throw Error('H8_FORBIDDEN_CAPABILITY_USED');
 const result={schema_version:'1.0.0',lock_id:lock.id,lock_sha256:lock.lock_sha256,purpose:lock.purpose,run_id:options.run_id,out_dir:relative(root,`${runRoot}/dist`).replaceAll('\\','/'),source_graph:verified.graph.paths,loaded_modules:[...modules].sort(),wrapper_sha256:sha(wrapper),forbidden_import_attempts:forbiddenAttempts,network_attempts:networkAttempts,llm_calls:0,media_search:0,sampler_calls:0,provider_calls:0,new_spend:0,wall_seconds:(performance.now()-started)/1000,approval:lock.approval};
 await writeFile(`${runRoot}/build-receipt.json`,JSON.stringify(result,null,2)+'\n');return result;
}
