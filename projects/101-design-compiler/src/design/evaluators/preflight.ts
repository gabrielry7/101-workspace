import {EvaluatorFlagsV1,DesignRefinementV1} from './contracts.ts';
export function guidedRefinement(rawFlags:unknown,evidence:{impeccable_guidance?:{path:string;sha256:string}[];raven_principles?:{id:string}[];raven_pattern_ok?:boolean}){
 const flags=EvaluatorFlagsV1.parse(rawFlags),refinement=DesignRefinementV1.parse({schema_version:'1.0.0'});
 if(flags.impeccable){if(!evidence.impeccable_guidance?.some(f=>f.path.endsWith('/reference/craft-floor.md')))throw Error('IMPECCABLE_GUIDANCE_MISSING');refinement.tracking='natural';refinement.label_placement='after-title';}
 if(flags.raven){const ids=evidence.raven_principles?.map(p=>p.id)??[];if(!ids.includes('text-readability')||!ids.includes('touch-target-size')||!evidence.raven_pattern_ok)throw Error('RAVEN_GUIDANCE_MISSING');refinement.reading_measure='bounded';refinement.touch_targets='comfortable';refinement.type_rhythm='reading';}
 return refinement;
}
