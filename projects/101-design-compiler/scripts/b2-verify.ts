import {readFile} from 'node:fs/promises';
import sharp from 'sharp';
import {loadB2Library} from './load-b2-library.ts';
import {compileReferenceCorpus} from '../src/media/reference-corpus.ts';
import {diagnoseBoundMedia} from '../src/requirements/media-diagnostic.ts';
import {hashBytes,verifyProtectedFiles} from './lib/correction-run.ts';
// Offline replay only. No acquisition, mutation, recipe writer or provider call.
const historical=process.argv.includes('--historical-replay');
const snapshot=JSON.parse(await readFile('data/media/library-v1/usda-pilot.json','utf8'));
const {library,handle,diagnostic,evaluated_at}=await loadB2Library(historical?{evaluation_time:snapshot.manifest.evaluated_at}:{});
const corpus=compileReferenceCorpus(await readFile('data/reference/design/101_referencias_aprobadas_completas_v01.md'));
if(await readFile('data/reference/design/corpus-v1.json','utf8')!==JSON.stringify(corpus,null,2)+'\n')throw Error('CORPUS_REPLAY_MISMATCH');
const tech=JSON.parse(await readFile(library.technical_inspection.path,'utf8'));
if(tech.tool.sharp!==sharp.versions.sharp||tech.tool.vips!==sharp.versions.vips||tech.tool.webp!==sharp.versions.webp)throw Error('DERIVATION_TOOLCHAIN_MISMATCH');
const original=await readFile(library.files.find(f=>f.asset_id==='b2-usda-d255-original')!.path);
for(const width of [480,960]){
 const actual=await sharp(original).resize({width,withoutEnlargement:true}).webp({quality:82,effort:6}).toBuffer();
 const stored=library.files.find(f=>f.asset_id===`b2-usda-d255-${width}`)!;
 if(hashBytes(actual)!==stored.sha256||actual.length!==stored.bytes)throw Error('DERIVATIVE_BYTE_REPLAY_MISMATCH');
}
const overlay=diagnoseBoundMedia(diagnostic,handle,evaluated_at);
if(overlay.entries.some(e=>e.status==='SATISFIED'))throw Error('ATMOSPHERE_MUST_NOT_COMPLETE_DOCUMENTARY_REQUIREMENTS');
const protection=await verifyProtectedFiles('docs/evidence/corrections/b2/pre/preservation.json');
console.log(JSON.stringify({status:'PASS_READ_ONLY',mode:historical?'HISTORICAL_REPLAY_NOT_CURRENT_AUTHORIZATION':'CURRENT_USE_EVALUATION',evaluated_at,library_sha256:library.library_sha256,assets:library.files.length,
 usages:library.bindings.length,requests:library.requests.length,corpus_references:corpus.references.length,derivatives_reproduced:2,protection,
 operational:'NOT_CONNECTED',human_design_approval:'NOT_COLLECTED'}));
