import {readFile,writeFile,mkdir} from 'node:fs/promises';
import ts from 'typescript';
const base=await readFile('src/composition/observe.ts','utf8'),extra=await readFile('src/design/evaluators/observe.ts','utf8');
// CUA's read-only DOM scope does not expose Performance or matchMedia. Keep the existing
// binding/geometry observer; omit those unavailable metrics, rather than inventing zeroes.
const from=base.indexOf('    resources:performance.'),to=base.indexOf('    animated_elements:');
if(from<0||to<from)throw Error('BASE_OBSERVER_ADAPTER_DRIFT');
const compatible=base.slice(0,from)+'    resources: null, navigation_duration_ms:null, reduced_motion:null,\n'+base.slice(to);
const js=ts.transpileModule('const parseFloat=Number.parseFloat,parseInt=Number.parseInt;\n'+compatible+'\n'+extra,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,newLine:ts.NewLineKind.LineFeed}}).outputText.replaceAll('export function','function');
await mkdir('.tools/design-tools',{recursive:true});await writeFile('.tools/design-tools/observer.js',js);console.log('Observer compiled: .tools/design-tools/observer.js');
