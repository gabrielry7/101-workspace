import {readFileSync,readdirSync,writeFileSync} from 'node:fs';
import {resolve,dirname,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=dirname(fileURLToPath(import.meta.url)),dist=resolve(root,'dist');
function walk(dir){return readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(resolve(dir,e.name)):[resolve(dir,e.name)])}
const files=walk(dist).map(p=>({path:relative(dist,p).replaceAll('\\','/'),sha256:createHash('sha256').update(readFileSync(p)).digest('hex')})).sort((a,b)=>a.path.localeCompare(b.path));
writeFileSync(resolve(root,'preview-files.json'),JSON.stringify({schema_version:'101-portable-preview-v1',snapshot:'locally-rebuilt-not-original-reviewed-snapshot',files},null,2)+'\n');
console.log(`Sealed ${files.length} rebuilt files. These need a new visual review.`);
