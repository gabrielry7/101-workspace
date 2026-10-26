// Same-host preparation follows scripts/b3-materialize.mjs: verified existing
// media package plus junctions to already installed dependencies/runtime.
// No downloads, credentials, user changes or model calls.
import {readFile,mkdir,copyFile,symlink,access,realpath,writeFile} from 'node:fs/promises';
import {resolve,relative,isAbsolute,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {root} from './bridge.mjs';
const id=process.argv[2];if(!/^[a-z0-9][a-z0-9-]{0,63}$/.test(id??''))throw Error('Task ID required');
const state=JSON.parse(await readFile(resolve(root,`.tools/claude-code/${id}/state.json`),'utf8'));
const target=await realpath(state.worktree),expected=await realpath(resolve(root,`.tools/claude-worktrees/${id}`));
if(target!==expected)throw Error('Unexpected worktree');
function within(base,path){const full=resolve(base,path),rel=relative(base,full);if(isAbsolute(rel)||rel.startsWith('..'))throw Error('Path rejected');return full;}
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const pack=JSON.parse(await readFile(resolve(root,'data/media/demo-v1/pixabay-fictional.json'),'utf8'));
const copied=[];
for(const f of pack.files){
  if(!f.path.startsWith('.tools/b2-demo/originals/')&&!f.path.startsWith('public/media/b2-fictional/'))throw Error('Non-package path');
  const bytes=await readFile(within(root,f.path));if(bytes.length!==f.bytes||sha(bytes)!==f.sha256)throw Error('Media source hash mismatch');
  const to=within(target,f.path);await mkdir(dirname(to),{recursive:true});
  if(await access(to).then(()=>true,()=>false)){if(sha(await readFile(to))!==f.sha256)throw Error('Existing worktree file differs');}
  else await copyFile(within(root,f.path),to);
  copied.push({path:f.path,sha256:f.sha256,bytes:f.bytes});
}
// B3 additionally consumes the already-reviewed silent derivative; it is not
// part of the earlier B2 package inventory and must not be regenerated here.
const experience=JSON.parse(await readFile(resolve(root,'data/media/demo-v1/b3-experience-review.json'),'utf8'));
for(const asset of experience.assets.filter(a=>a.uri.startsWith('/media/b3-experience/'))){
  const path='public'+asset.uri,bytes=await readFile(within(root,path));
  if(sha(bytes)!==asset.file_sha256)throw Error('B3 derivative hash mismatch');
  const to=within(target,path);await mkdir(dirname(to),{recursive:true});
  if(await access(to).then(()=>true,()=>false)){if(sha(await readFile(to))!==asset.file_sha256)throw Error('Existing B3 derivative differs');}
  else await copyFile(within(root,path),to);
  copied.push({path,sha256:asset.file_sha256,bytes:bytes.length});
}
const runtime=JSON.parse(await readFile(resolve(root,'docs/evidence/corrections/b2/runtime.json'),'utf8'));
for(const path of ['node_modules','.tools/node-v24.21.0-win-x64',runtime.browser_root]){
  const from=within(root,path),to=within(target,path);
  if(await access(to).then(()=>true,()=>false)){if(await realpath(to)!==await realpath(from))throw Error('Existing runtime path differs');}
  else {await mkdir(dirname(to),{recursive:true});await symlink(from,to,'junction');}
}
await writeFile(resolve(root,`.tools/claude-code/${id}/preparation.json`),JSON.stringify({kind:'EXISTING_B3_SAME_HOST_PACKAGE',worktree:target,copied,sharedRuntime:['node_modules','.tools/node-v24.21.0-win-x64',runtime.browser_root],credentialsCopied:false,downloads:0},null,2)+'\n');
console.log(JSON.stringify({worktree:target,mediaFiles:copied.length,sharedExistingRuntime:true}));
