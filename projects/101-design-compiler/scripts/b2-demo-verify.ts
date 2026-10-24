import {readFile} from 'node:fs/promises';
import sharp from 'sharp';
import {loadDemoPackage} from '../src/media/demo-package.ts';
import {byteSha256} from '../src/media/package.ts';
import {verifyProtectedFiles} from './lib/correction-run.ts';
const historical=process.argv.includes('--historical-replay'),snapshot=JSON.parse(await readFile('data/media/demo-v1/pixabay-fictional.json','utf8'));
const {pack}=await loadDemoPackage(historical?{evaluation_time:snapshot.evaluated_at}:{});
for(const source of pack.sources.filter(s=>s.provider_id!==149678)){
 const original=await readFile(pack.files.find(f=>f.asset_id===source.asset_id)!.path);
 for(const width of [640,1280]){
  const out=await sharp(original).resize({width,withoutEnlargement:true}).webp({quality:84,effort:6}).toBuffer(),file=pack.files.find(f=>f.asset_id===`pixabay-${source.provider_id}-${width}`)!;
  if(out.length!==file.bytes||byteSha256(out)!==file.sha256)throw Error('DEMO_IMAGE_DERIVATIVE_REPLAY_MISMATCH');
 }
}
console.log(JSON.stringify({status:'PASS_OFFLINE',mode:historical?'HISTORICAL_REPLAY_NOT_CURRENT_AUTHORIZATION':'CURRENT_USE',package_sha256:pack.package_sha256,photographs:4,silent_videos:1,images_reproduced:8,files:pack.files.length,usages:pack.usages.length,
 protection:await verifyProtectedFiles('docs/evidence/corrections/b2-demo/pre/preservation.json'),private_media_required:true,human_aesthetic_approval:'NOT_COLLECTED'}));
