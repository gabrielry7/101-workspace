import { mkdir, readFile, writeFile, cp, copyFile, access } from 'node:fs/promises';
import { resolve } from 'node:path';
import os from 'node:os';
import { z } from 'zod';
import { fontFingerprint, installedFingerprint } from './lock-files.ts';
import { inputSha256 } from '../../src/upstream/v1/protocol.ts';
import { hashBytes, treeHashes, workspacePath } from './correction-run.ts';
const file = z.strictObject({ path: z.string(), bytes: z.number().int().nonnegative(), sha256: z.string().regex(/^[a-f0-9]{64}$/) });
const pin = z.strictObject({ path: z.string(), sha256: z.string(), normalization: z.enum(['BINARY','LF_TEXT']) });
export const RuntimeSnapshotV1 = z.strictObject({ schema_version: z.literal('1.0.0'), kind: z.literal('B0_LOCAL_RUNTIME_SNAPSHOT'),
 scope: z.literal('SAME_WINDOWS_HOST_ISOLATED_BROWSER_NO_UPDATER'), browser_root: z.string(), browser_version: z.string(),
 browser_files: z.array(file).min(1), node_version: z.string(), node_sha256: z.string(), platform: z.string(), arch: z.string(),
 os_release: z.string(), os_version: z.string(), fonts: z.array(pin).min(1), installed_dependencies: z.array(pin).min(1),
 package_sha256: z.string(), package_lock_sha256: z.string(), snapshot_sha256: z.string() });
export type RuntimeSnapshot = z.infer<typeof RuntimeSnapshotV1>;
export const runtimeDigest = (snapshot: RuntimeSnapshot) => { const { snapshot_sha256: _digest, ...body } = snapshot; return inputSha256(body); };
export const snapshotPath = 'docs/evidence/corrections/b0/runtime.json';
export async function prepareRuntime() {
 if (await access(snapshotPath).then(() => true, () => false)) return verifyRuntime();
 const legacy = JSON.parse(await readFile('fixtures/locks/h8/pilot-flow.json','utf8'));
 const version = String(legacy.toolchain.browser_version).replace('Edg/','');
 if (!/^\d+\.\d+\.\d+\.\d+$/.test(version)) throw Error('B0_INVALID_BROWSER_VERSION');
 const source = `C:/Program Files (x86)/Microsoft/Edge/Application/${version}`;
 for (const pin of legacy.toolchain.browser_files) {
  const name = String(pin.path).split('/').at(-1)!;
  if (hashBytes(await readFile(`${source}/${name}`)) !== pin.sha256) throw Error('B0_LEGACY_BROWSER_BYTES_NOT_AVAILABLE');
 }
 const browser_root = `.tools/corrections/b0/browser-${version}`, destination = workspacePath(process.cwd(),browser_root);
 if (await access(destination).then(() => true, () => false)) throw Error('B0_BROWSER_DIRECTORY_ALREADY_EXISTS_WITHOUT_RECEIPT');
 await mkdir(destination,{recursive:true});
 await cp(source,`${destination}/${version}`,{recursive:true,force:false,errorOnExist:true,dereference:true});
 await copyFile(`${source}/msedge.exe`,`${destination}/msedge.exe`);
 const body = { schema_version:'1.0.0',kind:'B0_LOCAL_RUNTIME_SNAPSHOT',scope:'SAME_WINDOWS_HOST_ISOLATED_BROWSER_NO_UPDATER',
  browser_root,browser_version:legacy.toolchain.browser_version,browser_files:await treeHashes(destination),
  node_version:process.version,node_sha256:hashBytes(await readFile(process.execPath)),platform:process.platform,arch:process.arch,
  os_release:os.release(),os_version:os.version(),fonts:await fontFingerprint(),installed_dependencies:await installedFingerprint(process.cwd()),
  package_sha256:hashBytes(await readFile('package.json')),package_lock_sha256:hashBytes(await readFile('package-lock.json')) };
 const snapshot = RuntimeSnapshotV1.parse({...body,snapshot_sha256:inputSha256(body)});
 await writeFile(snapshotPath,JSON.stringify(snapshot,null,2)+'\n');
 return verifyRuntime();
}
export async function verifyRuntime(path = snapshotPath): Promise<RuntimeSnapshot> {
 const snapshot = RuntimeSnapshotV1.parse(JSON.parse(await readFile(path,'utf8')));
 if (runtimeDigest(snapshot)!==snapshot.snapshot_sha256) throw Error('B0_RUNTIME_RECEIPT_CHANGED');
 if (snapshot.node_version!==process.version||snapshot.node_sha256!==hashBytes(await readFile(process.execPath))||snapshot.platform!==process.platform||snapshot.arch!==process.arch) throw Error('B0_NODE_DRIFT');
 if (snapshot.os_release!==os.release()||snapshot.os_version!==os.version()||inputSha256(snapshot.fonts)!==inputSha256(await fontFingerprint())) throw Error('B0_OS_OR_FONTS_DRIFT');
 if (snapshot.package_sha256!==hashBytes(await readFile('package.json'))||snapshot.package_lock_sha256!==hashBytes(await readFile('package-lock.json'))||inputSha256(snapshot.installed_dependencies)!==inputSha256(await installedFingerprint(process.cwd()))) throw Error('B0_DEPENDENCIES_DRIFT');
 const current = await treeHashes(workspacePath(process.cwd(),snapshot.browser_root));
 if (inputSha256(current)!==inputSha256(snapshot.browser_files)) throw Error('B0_BROWSER_SNAPSHOT_DRIFT');
 return snapshot;
}
export const controlledBrowserPath = (snapshot: RuntimeSnapshot) => resolve(workspacePath(process.cwd(),snapshot.browser_root),'msedge.exe');
