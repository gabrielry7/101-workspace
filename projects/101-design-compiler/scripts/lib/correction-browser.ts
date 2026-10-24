import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import type {openLocalBrowser} from './local-browser.ts';
import {hashBytes,workspacePath} from './correction-run.ts';

// A documented launch overlay of the existing QA harness, not a second renderer.
// Windows refuses the copied Edge renderer with its normal sandbox. This mode is
// limited to our fixed local test build; it must never be used to visit providers.
export const B0_BROWSER_FLAGS=['--no-sandbox','--disable-background-networking','--disable-component-update','--disable-sync'] as const;
export function browserSourceOverlay(source:string) {
 const needle="'--headless=new','--disable-gpu'";
 if(source.split(needle).length!==2)throw Error('B0_BROWSER_OVERLAY_SOURCE_CHANGED');
 return source.replace(needle,`${needle},${B0_BROWSER_FLAGS.map(flag=>JSON.stringify(flag)).join(',')}`);
}
export async function prepareBrowserHarness() {
 const source=await readFile('scripts/lib/local-browser.ts','utf8'),adapted=browserSourceOverlay(source),digest=hashBytes(adapted);
 const folder=workspacePath(process.cwd(),'.tools/corrections/b0/harness');await mkdir(folder,{recursive:true});
 const path=resolve(folder,`browser-${digest}.ts`);
 if(await access(path).then(()=>true,()=>false)) {
  if(hashBytes(await readFile(path))!==digest)throw Error('B0_BROWSER_HARNESS_DRIFT');
 } else await writeFile(path,adapted);
 const module=await import(pathToFileURL(path).href) as {openLocalBrowser:typeof openLocalBrowser};
 const open=async(out:string)=>{
  if(!resolve(out).startsWith(resolve('.tools/corrections/b0')+'/')&&!resolve(out).startsWith(resolve('.tools/corrections/b0')+'\\'))throw Error('B0_BROWSER_LOCAL_BUILD_ONLY');
  return module.openLocalBrowser(out);
 };
 return {open,adapted,provenance:{source:'scripts/lib/local-browser.ts',source_sha256:hashBytes(source),adapted_sha256:digest,
  flags:B0_BROWSER_FLAGS,sandbox:'DISABLED_ONLY_FOR_FIXED_LOCAL_TEST_PAGES',production_browser:false}};
}
