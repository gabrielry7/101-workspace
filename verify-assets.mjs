import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const root=path.resolve(process.argv[2]||process.cwd());
const manifest=JSON.parse(fs.readFileSync(path.join(root,'asset-manifest.json'),'utf8').replace(/^\uFEFF/,''));
let count=0;
for(const file of manifest.files){
 const target=path.resolve(root,file.path),relative=path.relative(root,target);
 if(relative.startsWith('..')||path.isAbsolute(relative))throw Error('Unsafe manifest path');
 const stat=fs.statSync(target);if(stat.size!==file.bytes)throw Error('Restored size mismatch: '+file.path);
 const hash=createHash('sha256');
 if(stat.size<=32*1024*1024)hash.update(fs.readFileSync(target));else for await(const chunk of fs.createReadStream(target))hash.update(chunk);
 if(hash.digest('hex')!==file.sha256)throw Error('Restored SHA256 mismatch: '+file.path);
 if(++count%5000===0)console.log(`Verified assets: ${count}/${manifest.files.length}`);
}
console.log(`RESTORATION_PASS files=${count} archives=${manifest.archives.length}`);
