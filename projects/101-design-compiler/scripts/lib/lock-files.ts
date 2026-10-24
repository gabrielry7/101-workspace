import { readFile,readdir } from 'node:fs/promises';
import { resolve,relative,dirname,isAbsolute } from 'node:path';
import { createHash } from 'node:crypto';
import type { z } from 'zod';
import type { DependencyFingerprintV1 } from '../../src/lock/contracts.ts';
export type Fingerprint=z.infer<typeof DependencyFingerprintV1>;
export const sha=(bytes:Uint8Array|string)=>createHash('sha256').update(bytes).digest('hex');
export function within(root:string,path:string){const target=resolve(root,path),r=relative(resolve(root),target);if(r.startsWith('..')||isAbsolute(r))throw Error('LOCK_PATH_OUTSIDE_ROOT');return target;}
export async function fingerprint(root:string,path:string,normalization:Fingerprint['normalization']='LF_TEXT'):Promise<Fingerprint>{const b=await readFile(within(root,path));return {path,sha256:sha(normalization==='LF_TEXT'?b.toString('utf8').replace(/\r\n/g,'\n'):b),normalization};}
export async function fileTree(root:string,prefix:string):Promise<string[]>{const paths:string[]=[];const walk=async(path:string)=>{for(const e of await readdir(within(root,path),{withFileTypes:true})){if(['.astro','.vite','.cache'].includes(e.name))continue;const next=`${path}/${e.name}`;if(e.isDirectory())await walk(next);else if(e.isFile())paths.push(next);}};await walk(prefix);return paths.sort();}
export async function sourceGraph(root:string,entries:string[]){const seen=new Set<string>();const externals=new Set<string>();const walk=async(path:string)=>{if(seen.has(path))return;seen.add(path);const text=await readFile(within(root,path),'utf8');
 for(const match of text.matchAll(/(?:import|export)\s+(?!type\b)(?:[^;\n]*?\s+from\s+)?['"]([^'"]+)['"]/g)){const raw=match[1]!.split('?')[0]!;if(raw.startsWith('.')){const target=relative(root,resolve(dirname(within(root,path)),raw)).replaceAll('\\','/');await walk(target);}else externals.add(raw);}};
 for(const p of entries)await walk(p);const paths=[...seen].sort();const forbidden=paths.filter(p=>/src\/design\/search\.ts$|scripts\/load-|scripts\/record-|scripts\/reserve-|src\/planner\/plan\.ts$/.test(p));if(forbidden.length)throw Error(`FORBIDDEN_REBUILD_GRAPH:${forbidden.join(',')}`);return {paths,externals:[...externals].sort(),fingerprints:await Promise.all(paths.map(p=>fingerprint(root,p)))};}
export async function installedFingerprint(root:string){const paths=await fileTree(root,'node_modules');const result:Fingerprint[]=[];for(let i=0;i<paths.length;i+=32)result.push(...await Promise.all(paths.slice(i,i+32).map(p=>fingerprint(root,p,'BINARY'))));return result;}
export const browserRoot='C:/Program Files (x86)/Microsoft/Edge/Application';
export async function browserFingerprint(){const pkg=await readdir(browserRoot,{withFileTypes:true});const versions=pkg.filter(e=>e.isDirectory()&&/^\d+\.\d+\.\d+\.\d+$/.test(e.name)).map(e=>e.name).sort();const version=versions.at(-1);if(!version)throw Error('CONTROLLED_BROWSER_MISSING');const paths=['msedge.exe',`${version}/msedge.dll`,`${version}/icudtl.dat`,`${version}/resources.pak`];return {version:`Edg/${version}`,files:await Promise.all(paths.map(p=>fingerprint(browserRoot,p,'BINARY')))};}
export const fontRoot='C:/Windows';
export async function fontFingerprint(){const files=await readdir(`${fontRoot}/Fonts`);return Promise.all(files.filter(f=>/^(?:segoeui|segui|georgia|georgiab|georgiai|georgiaz|times|arial)/i.test(f)&&/\.(?:ttf|ttc|otf)$/i.test(f)).sort().map(f=>fingerprint(fontRoot,`Fonts/${f}`,'BINARY')));}
