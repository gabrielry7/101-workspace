import {z} from 'zod';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {byteSha256} from './package.ts';
const text=z.string().min(1),sha=z.string().regex(/^[a-f0-9]{64}$/);
export const ReferenceCorpusV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('REPORTED_DESIGN_REFERENCE_CORPUS'),
 corpus_sha256:sha,source_path:text,source_bytes_sha256:sha,source_bytes:z.number().int().positive(),
 source_authority:z.literal('USER_SUPPLIED_SUMMARY_NOT_NEW_VOTES'),references:z.array(z.strictObject({id:text,number:z.number().int().positive(),name:text,url:z.url(),sector:text,
  reported_status:z.enum(['SITIO_POSITIVO','ELEMENTO_POSITIVO']),approved_scope:z.enum(['GLOBAL_REPORTED','SPECIFIC_PAGE_ONLY','STORYTELLING_ONLY','DROPDOWN_ONLY']),
  reported_intensity_literal:text,source_section_literal:text,negative_or_limit_lines:z.array(text),new_observations:z.array(text).max(0),
  inspected_at:z.null(),captured_viewports:z.array(text).max(0),asset_reuse:z.literal('NOT_AUTHORIZED_BY_REFERENCE')})),
 negative_references_section_literal:text,training:z.literal('NOT_PERFORMED'),human_approval_of_generated_sites:z.literal('NOT_COLLECTED')});
export function compileReferenceCorpus(bytes:Uint8Array){
 const source=Buffer.from(bytes).toString('utf8'),rows=[...source.matchAll(/^\| (\d+) \| \[([^\]]+)\]\((https:[^)]+)\) \| ([^|]+) \| `(SITIO_POSITIVO|ELEMENTO_POSITIVO)` \| ([^|]+) \|\r?$/gm)];
 const headings=[...source.matchAll(/^### (\d+)\. .+\r?$/gm)];
 if(rows.length!==21||headings.length!==21)throw Error('REFERENCE_SOURCE_STRUCTURE_CHANGED');
 const references=rows.map(row=>{
  const number=Number(row[1]),h=headings.find(h=>Number(h[1])===number);if(!h)throw Error('REFERENCE_SECTION_MISSING');
  const start=h.index!,separator=source.indexOf('\n---',start),next=headings.find(candidate=>candidate.index!>start)?.index??source.length;
  const section=source.slice(start,Math.min(next,separator<0?source.length:separator));
  return {id:`reference-${String(number).padStart(2,'0')}`,number,name:row[2]!,url:row[3]!,sector:row[4]!.trim(),reported_status:row[5]!,
   approved_scope:number===12?'SPECIFIC_PAGE_ONLY':number===13?'STORYTELLING_ONLY':number===21?'DROPDOWN_ONLY':'GLOBAL_REPORTED',
   reported_intensity_literal:row[6]!.trim(),source_section_literal:section,
   negative_or_limit_lines:section.split(/\r?\n/).filter(l=>/Problema advertido|Límite|no entusiasma/.test(l)),new_observations:[],inspected_at:null,captured_viewports:[],asset_reuse:'NOT_AUTHORIZED_BY_REFERENCE'};
 });
 if(references.filter(r=>r.reported_status==='SITIO_POSITIVO').length!==18||references.filter(r=>r.reported_status==='ELEMENTO_POSITIVO').length!==3)throw Error('REFERENCE_SCOPE_COUNTS_CHANGED');
 const negativeStart=source.indexOf('## III.'),negativeEnd=source.indexOf('## IV.');if(negativeStart<0||negativeEnd<=negativeStart)throw Error('REFERENCE_NEGATIVES_MISSING');
 const body={schema_version:'1.0.0',kind:'REPORTED_DESIGN_REFERENCE_CORPUS',source_path:'data/reference/design/101_referencias_aprobadas_completas_v01.md',
  source_bytes_sha256:byteSha256(bytes),source_bytes:bytes.length,source_authority:'USER_SUPPLIED_SUMMARY_NOT_NEW_VOTES',references,
  negative_references_section_literal:source.slice(negativeStart,negativeEnd),training:'NOT_PERFORMED',human_approval_of_generated_sites:'NOT_COLLECTED'};
 return ReferenceCorpusV1.parse({...body,corpus_sha256:inputSha256(body)});
}
