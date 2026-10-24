import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {compileReferenceCorpus} from '../src/media/reference-corpus.ts';
const corpus=compileReferenceCorpus(await readFile('data/reference/design/101_referencias_aprobadas_completas_v01.md'));
const path='data/reference/design/corpus-v1.json',bytes=JSON.stringify(corpus,null,2)+'\n';
if(process.argv.includes('--verify')){if(await readFile(path,'utf8')!==bytes)throw Error('REFERENCE_CORPUS_REPLAY_MISMATCH');}
else{await mkdir('data/reference/design',{recursive:true});await writeFile(path,bytes);}
console.log(JSON.stringify({status:process.argv.includes('--verify')?'VERIFIED_READ_ONLY':'EXPORTED',references:corpus.references.length,corpus_sha256:corpus.corpus_sha256}));
