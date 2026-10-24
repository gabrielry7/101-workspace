import {inputSha256} from '../../upstream/v1/protocol.ts';
import {DesignFindingV1,type DesignFinding} from './contracts.ts';
export function makeFinding(source:{tool:string;version:string;receipt_sha256:string},location:{route:string;viewport:string},rule:string,evidence:unknown,recommendation:string,options:Partial<Pick<DesignFinding,'kind'|'severity'|'selector'|'repair'|'confidence'>>={}){
 return DesignFindingV1.parse({schema_version:'1.0.0',id:inputSha256({source,location,rule,evidence}).slice(0,24),rule,kind:'HEURISTIC',severity:'WARNING',selector:'',repair:'NONE',confidence:.8,...location,...options,evidence:[typeof evidence==='string'?evidence:JSON.stringify(evidence)],recommendation,sources:[source]});
}
export function normalizeImpeccable(receipt:any,location:{route:string;viewport:string}){
 const source={tool:receipt.tool,version:receipt.version,receipt_sha256:inputSha256(receipt)};
 return receipt.findings.map((f:any)=>makeFinding(source,location,f.antipattern,{file:f.file,line:f.line,snippet:f.snippet},f.description,{kind:f.category==='slop'?'AESTHETIC':'HEURISTIC',
  repair:f.antipattern==='wide-tracking'?'TRACKING':f.antipattern==='small-touch-target'?'TOUCH_TARGETS':f.antipattern==='long-line-length'?'READING_MEASURE':'NONE',confidence:f.category==='slop'?.6:.85}));
}
export function normalizeRaven(receipt:any,location:{route:string;viewport:string}){
 const source={tool:`raven.${receipt.tool}`,version:receipt.version,receipt_sha256:inputSha256(receipt)},out=receipt.output,findings:DesignFinding[]=[];
 if(receipt.status!=='OK')return [makeFinding(source,location,'TOOL_UNAVAILABLE',out,'Resolve the tool failure; do not treat an unavailable audit as a pass.',{kind:'MEASURED',severity:'BLOCKING',confidence:1})];
 if(receipt.tool==='audit_tap_targets')for(const f of out.fix_table??[])findings.push(makeFinding(source,location,'TARGET_44',f,f.fix,{kind:'MEASURED',selector:f.selector,repair:'TOUCH_TARGETS',confidence:1}));
 if(receipt.tool==='audit_contrast')for(const f of (out.aa_failures??out.rows?.filter((v:any)=>v.status==='fail'||v.aa===false)??[]))findings.push(makeFinding(source,location,'CONTRAST_AA',f,'Correct the foreground/background token only after confirming the effective backdrop.',{kind:'MEASURED',severity:'BLOCKING',selector:f.selector,confidence:.95}));
 for(const f of out.findings??[]){if(!f||typeof f!=='object'||f.status==='pass')continue;findings.push(makeFinding(source,location,f.rule??f.code??f.check??'LAYOUT_HEURISTIC',f,f.fix??f.recommendation??f.message??'Inspect the rendered evidence before changing composition.',{selector:f.selector??'',confidence:.7,repair:'NONE'}));}
 return findings;
}
