import {mkdir,cp,readdir,readFile,access} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'astro';

// Verification-only route selection. A byte-identical copy of the current
// source is compiled by the same Astro installation, without editing old gates.
const root=fileURLToPath(new URL('../../',import.meta.url));
const staged=join(root,'.tools/footer-preview-'+process.pid+'/src');
await mkdir(join(staged,'pages'),{recursive:true});
for(const [target,source] of [
  [join(staged,'pages/bones'),join(root,'src/pages/bones')],
  [join(staged,'components/bones'),join(root,'src/components/bones')],
  [join(staged,'bones/footer'),join(root,'src/bones/footer')],
]){
  await cp(source,target,{recursive:true,errorOnExist:true,force:false});
  for(const path of await readdir(source,{recursive:true,withFileTypes:true})){
    if(!path.isFile())continue;
    const relative=resolve(path.parentPath,path.name).slice(resolve(source).length+1);
    if(!(await readFile(join(source,relative))).equals(await readFile(join(target,relative))))throw Error('Staged source differs: '+relative);
  }
}
const previewPublic=resolve(staged,'../public');
await mkdir(previewPublic,{recursive:true});
for(const [source,name] of [
  [join(root,'.tools/footer-inspector'),'__bone-tools'],
  [join(root,'.tools/footer-reference'),'__bone-references'],
]){
  try{await access(source);}catch{continue;}
  await cp(source,join(previewPublic,name),{recursive:true});
}
process.env.BONES_PREVIEW='1';
await build({root,srcDir:staged,outDir:join(root,'dist-footer-bones'),publicDir:previewPublic});
