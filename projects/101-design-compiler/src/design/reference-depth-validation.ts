import {inputSha256} from '../upstream/v1/protocol.ts';
export function validateReferenceDepth(research:any,prior:any){
 const expected=[...prior.references.map((r:any)=>({id:r.id,url:r.url,scope:r.approved_scope})),{id:'reference-22',url:'https://pizza4ps.com/kh/',scope:'NEW_REFERENCE_NO_VOTE'},{id:'reference-23',url:'https://www.artek.fi/en/',scope:'NEW_REFERENCE_NO_VOTE'}];
 if(inputSha256(research.coverage.map(({id,url,scope}:any)=>({id,url,scope})))!==inputSha256(expected))throw Error('DEPTH_REFERENCE_SCOPE_CHANGED');
 const ids=new Set(expected.map((r:any)=>r.id));if(new Set(research.features.map((f:any)=>f.id)).size!==research.features.length||research.features.some((f:any)=>f.references.some((id:string)=>!ids.has(id))||f.disposition==='IMPLEMENT_SHARED'&&!f.operator||f.disposition==='NEEDS_DATA'&&!f.required_data.length))throw Error('DEPTH_RESEARCH_BINDING_INVALID');
}
