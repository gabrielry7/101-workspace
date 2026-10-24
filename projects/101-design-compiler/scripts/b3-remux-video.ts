import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {videoOnlyMp4} from '../src/media/remux-video.ts';
import {byteSha256} from '../src/media/package.ts';
const source='.tools/b2-demo/originals/149678.mp4',target='public/media/b3-experience/149678-silent-1280.mp4',receipt='docs/evidence/corrections/b3/experience-media-01/remux.json';
const input=await readFile(source);if(byteSha256(input)!=='37d5f583f0368d376dcb461b18b5c06021eeee92bed281dc16be4df2734223d0')throw Error('B3_SOURCE_VIDEO_CHANGED');const {output,...proof}=videoOnlyMp4(input);
const result={kind:'LOCAL_VIDEO_ONLY_LOSSLESS_REMUX',source,source_sha256:byteSha256(input),output:target,output_sha256:byteSha256(output),output_bytes:output.length,...proof,source_audio:'DROPPED_NOT_COPIED_OR_PLAYED',new_frames_or_upscaling:false};
if(process.argv.includes('--derive-reviewed-source')){if(await access(target).then(()=>true,()=>false))throw Error('B3_REMUX_EXISTS');await mkdir('public/media/b3-experience',{recursive:true});await mkdir('docs/evidence/corrections/b3/experience-media-01',{recursive:true});await writeFile(target,output);await writeFile(receipt,JSON.stringify(result,null,2)+'\n');}
else if(process.argv.includes('--verify')){if(byteSha256(await readFile(target))!==result.output_sha256||JSON.stringify(JSON.parse(await readFile(receipt,'utf8')))!==JSON.stringify(result))throw Error('B3_REMUX_REPLAY_MISMATCH');}
else throw Error('EXPLICIT_DERIVE_OR_VERIFY_REQUIRED');console.log(JSON.stringify(result));
