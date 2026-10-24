import {readFile,writeFile,mkdir} from 'node:fs/promises';
import ts from 'typescript';
export async function depthObserver(){
 const sources=await Promise.all(['experience','rich-experience','depth-experience'].map(n=>readFile(`src/design/${n}-audit.ts`,'utf8')));
 const raw=sources.map((s,i)=>{const name=['Experience','RichExperience','DepthExperience'][i];s=s.replaceAll('\r\n','\n');return s.slice(s.indexOf(`export function observe${name}`),s.indexOf(i===0?'const sorted=':`export function audit${name}`));}).join('\n');
 return ts.transpileModule(raw,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,newLine:ts.NewLineKind.LineFeed}}).outputText.replaceAll('export function','function');
}
if(process.argv.includes('--emit')){await mkdir('.tools',{recursive:true});await writeFile('.tools/b3-depth-observer.js',await depthObserver());console.log('.tools/b3-depth-observer.js');}
