import { PreferenceV1 } from './contracts.ts';
export function validatePreference(raw:unknown,pair:{id:string;context_sha256:string;left_id:string;right_id:string;left_sha256:string;right_sha256:string;left_screenshot_sha256:string;right_screenshot_sha256:string;semantic_page:string;viewport:{width:number;height:number}}){
 const parsed=PreferenceV1.safeParse(raw);if(!parsed.success)return {success:false,codes:['PREFERENCE_SCHEMA_OR_SIMULATION']};
 const value=parsed.data;
 const matches=value.comparison_id===pair.id&&(['context_sha256','left_id','right_id','left_sha256','right_sha256','left_screenshot_sha256','right_screenshot_sha256','semantic_page'] as const).every(key=>value[key]===pair[key])
  &&value.viewport.width===pair.viewport.width&&value.viewport.height===pair.viewport.height;
 return {success:matches,codes:matches?[]:['PREFERENCE_CONTEXT_MISMATCH']};
}
