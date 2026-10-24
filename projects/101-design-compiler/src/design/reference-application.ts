import {ReferenceCompositionV1} from './contextual-contracts.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
export function validateReferenceApplication(value:unknown,context:any,research:any,designs:any[],media:any){
 const r=ReferenceCompositionV1.parse(value);
 if(r.source_context_sha256!==inputSha256(context)||r.research_sha256!==inputSha256(research)||r.content_sha256!==context.scenario.content.content_sha256||r.media_sha256!==media.review_sha256)throw Error('B3_REFERENCE_CONTEXT_MISMATCH');
 if(research.authority!==r.authority||research.coverage.references!==21||research.coverage.representative_views!==42)throw Error('B3_REFERENCE_AUTHORITY_INVALID');
 if(new Set(r.variants.map(v=>v.id)).size!==designs.length||new Set(r.variants.map(v=>v.relationship)).size!==4||new Set(r.variants.map(v=>v.mobile)).size!==4)throw Error('B3_REFERENCE_DIVERSITY_INVALID');
 for(const v of r.variants){const d=designs.find(d=>d.id===v.id);
  if(!d||d.art_direction_id!==v.art_direction_id||v.palette!==d.tokens.palette||v.voice!==d.tokens.voice||v.references.some(id=>!context.references.some((r:any)=>r.id===id)))throw Error('B3_REFERENCE_VARIANT_INVALID');
 }
 return r;
}
