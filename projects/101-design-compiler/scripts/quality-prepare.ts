import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {qualityInputs} from './load-quality-lab.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {guidedRefinement} from '../src/design/evaluators/preflight.ts';
// Runtime import lives only in build tooling. No evaluator package enters the site bundle.
const bridge='../tooling/design-evaluation/raven-client.mjs';const {RavenSession}=await import(bridge);
const out='docs/evidence/design-evaluation/preflight';await mkdir(out,{recursive:true});
const inputs=await qualityInputs(),r=await new RavenSession().connect(),cases=[];
const guidePaths=['SKILL.md','reference/craft.md','reference/craft-floor.md','reference/audit.md','reference/polish.md','reference/distill.md'];
const guidance=await Promise.all(guidePaths.map(async p=>({path:`.agents/skills/impeccable/${p}`,sha256:inputSha256((await readFile(`.agents/skills/impeccable/${p}`,'utf8')).replaceAll('\r\n','\n'))})));
try{
 const taste=await r.call('list_taste_profiles',{});
 for(const input of inputs){const p=await r.call('get_principles',{context:`${input.id} editorial website typography mobile navigation spacing`,format:'checklist'}),pattern=await r.call('get_pattern',{type:'navigation',platform:'responsive',goal:'usability'});
  if(p.status!=='OK'||pattern.status!=='OK')throw Error('RAVEN_PREFLIGHT_FAILED');
  const ids=p.output.principles.map((v:any)=>v.id);if(!ids.includes('touch-target-size')||!ids.includes('text-readability'))throw Error('RAVEN_GUIDANCE_UNMAPPED');
  const variants=['A','B','C','D'].map(condition=>{const flags={impeccable:['B','D'].includes(condition),raven:['C','D'].includes(condition)},refinement=guidedRefinement(flags,{impeccable_guidance:guidance,raven_principles:p.output.principles,raven_pattern_ok:pattern.status==='OK'});
    return {condition,flags,design:input.design,refinement,iteration:0,trace:[...(flags.impeccable?[{source:'IMPECCABLE_AGENT_GUIDANCE',evidence:guidance,decisions:['tracking:natural','label_placement:after-title'],note:'Applied by this Codex session; not an autonomous CLI craft/polish call. Refinement of existing visual world, no new identity.'}]:[]),...(flags.raven?[{source:'RAVEN_MCP',principle_ids:['touch-target-size','text-readability'],principles_receipt:inputSha256(p),pattern_receipt:inputSha256(pattern),decisions:['reading_measure:bounded','touch_targets:comfortable','type_rhythm:reading']}]:[])]};});
  cases.push({id:input.id,input_sha256:inputSha256(input),data_mode:input.mode,variants});
 }
 const calls=r.calls;await writeFile(`${out}/raven.json`,JSON.stringify({tools:r.tools,calls,taste_status:taste.output.profiles?.length?'PROFILE_PRESENT_NOT_CALIBRATED':'NO_PROFILE_AUDIT_TASTE_SKIPPED'},null,2)+'\n');
 const artifact={schema_version:'1.0.0',experiment_id:inputSha256({inputs,guidance,versions:['4.7.0','0.1.16','2.6.0','1.32.1']}),seed_status:'EXISTING_SAVED_PLANS_FROM_SEEDED_SEARCH_IDENTICAL_IN_ALL_CONDITIONS',budget:{max_iterations:2,max_tool_calls:200,max_wall_seconds:600,max_new_spend:0},cases,
 metering:{preflight_tool_calls:calls.length,model_api_calls:0,session_tokens:null,session_cost:null,paid_provider_spend:0},human_preferences:'NOT_COLLECTED',default_enabled:false};
 await mkdir('data/derived/design-evaluation-v1',{recursive:true});await writeFile('data/derived/design-evaluation-v1/experiment.json',JSON.stringify(artifact,null,2)+'\n');console.log(JSON.stringify({status:'PREPARED',cases:cases.map(c=>c.id),conditions:4,preflight_calls:calls.length,experiment_id:artifact.experiment_id}));
}finally{await r.close();}
