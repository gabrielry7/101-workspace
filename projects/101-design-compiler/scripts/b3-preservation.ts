import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {hashBytes,verifyProtectedFiles} from './lib/correction-run.ts';
export const b3Preservation='docs/evidence/corrections/b3/pre/preservation.json';
if(process.argv.includes('--capture')){
 if(await access(b3Preservation).then(()=>true,()=>false))throw Error('B3_BASELINE_EXISTS');
 const args=['-c','safe.directory=C:/Users/gabri/101-design-compiler'],head=execFileSync('git',[...args,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
 if(head!=='1bf426424a41e51b58bdc0e09c1485b077dd3475')throw Error('B3_BASE_HEAD_MISMATCH');
 const paths=execFileSync('git',[...args,'ls-files','-z'],{encoding:'utf8',maxBuffer:32*1024*1024}).split('\0').filter(p=>p&&p!=='scripts/export-contracts.ts'),files=[];
 for(const path of paths){const raw=await readFile(path),normalization=path==='.gitattributes'||/\.(?:md|txt|json|ts|astro|css|mjs|ps1|py)$/.test(path)?'LF_UTF8':'BINARY',b=normalization==='BINARY'?raw:Buffer.from(raw.toString().replaceAll('\r\n','\n'));files.push({path,normalization,bytes:b.length,sha256:hashBytes(b)});}
 await mkdir('docs/evidence/corrections/b3/pre',{recursive:true});await writeFile(b3Preservation,JSON.stringify({head,allowed_prior_changes:['scripts/export-contracts.ts'],files},null,2)+'\n');
 console.log(JSON.stringify({status:'BASELINE_CAPTURED',files:files.length}));
}else if(process.argv.includes('--verify'))console.log(JSON.stringify(await verifyProtectedFiles(b3Preservation)));
