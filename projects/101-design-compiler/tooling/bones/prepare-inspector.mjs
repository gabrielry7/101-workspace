import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const root=fileURLToPath(new URL('../../',import.meta.url));
const source=resolve(process.env.BONES_REFERENCE_ROOT || join(root,'.tools/bones-handoff-20261105/source'));
const expected='6c0ed29940985bfb1789280c1972e47386775193';
const actual=execFileSync('git',['-C',source,'rev-parse','HEAD'],{encoding:'utf8',windowsHide:true}).trim();
if(actual!==expected)throw Error('Inspector source must match the reviewed commit '+expected);
const output=join(root,'.tools/footer-inspector');await mkdir(output,{recursive:true});
const files={};
for(const name of ['measure.js','guides.js']){
  const relative='packages/component-preview/'+name;
  const bytes=await readFile(join(source,relative));
  const committed=execFileSync('git',['-C',source,'show',expected+':'+relative],{maxBuffer:2e6,windowsHide:true});
  if(bytes.toString('utf8').replaceAll('\r\n','\n')!==committed.toString('utf8').replaceAll('\r\n','\n'))throw Error('Unreviewed inspector changes: '+name);
  await writeFile(join(output,name),committed);
  files[name]=createHash('sha256').update(committed).digest('hex');
}
await writeFile(join(output,'provenance.json'),JSON.stringify({owner:'101-world-model/packages/component-preview',commit:expected,files,redistribution:'local review only; ignored by Git'},null,2));
console.log(JSON.stringify({prepared:true,owner:'original component-preview',commit:expected,files}));
