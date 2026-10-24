import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {validateReferenceApplication} from '../src/design/reference-application.ts';
const read=async(p:string)=>JSON.parse(await readFile(p,'utf8'));
const context=await read('data/design/contextual-v2/context.json'),research=await read('data/reference/design/visual-review-2026-10-15.json'),designs=await read('data/design/contextual-v2/finalists.json'),media=await read('data/media/demo-v1/b3-usage-review.json');
const decisions=[
 {relationship:'EditorialCard',chapters:'Editorial',mobile:'ReadingFirst',references:['reference-19','reference-16','reference-04'],decision:'Ficha editorial junto a fotografía natural; primero lectura en móvil. La paleta cálida y la serif trabajan con la madera de la imagen, sin superponer texto sobre el stock.'},
 {relationship:'OffsetPair',chapters:'Direct',mobile:'CompactIndex',references:['reference-02','reference-06','reference-21'],decision:'Dos campos desplazados conectan título y fotografía sin invadir sus zonas legibles; filas alternas y un índice móvil nativo. No requiere una segunda imagen hero ni copia la arquitectura completa de Singer.'},
 {relationship:'TypeGallery',chapters:'Exhibit',mobile:'ImageSequence',references:['reference-17','reference-07','reference-12'],decision:'Una apertura tipográfica oscura y una imagen de escala contenida preceden una galería escalonada. Pausas editoriales y secuencia móvil sin ampliar el vídeo ni inferir un negocio nocturno.'},
 {relationship:'FramedCover',chapters:'Notebook',mobile:'CoverFirst',references:['reference-03','reference-06','reference-18','reference-13'],decision:'La foto enmarcada abre el recorrido visual antes de la ficha editorial; carta como cuaderno con columnas de índice y lectura. En móvil se conserva título accesible y aparece la foto antes de los detalles, sin introducción obligatoria.'},
];
const value=validateReferenceApplication({schema_version:'1.0.0',kind:'ASSISTANT_REFERENCE_APPLICATION',source_context_sha256:inputSha256(context),research_sha256:inputSha256(research),content_sha256:context.scenario.content.content_sha256,media_sha256:media.review_sha256,authority:'ASSISTANT_OBSERVATIONS_NOT_NEW_USER_VOTES',human_approval:'NOT_COLLECTED',variants:designs.map((d:any,i:number)=>({id:d.id,art_direction_id:d.art_direction_id,palette:d.tokens.palette,voice:d.tokens.voice,...decisions[i],media_policy:'NATURAL_RATIO_NO_CROP_STATIC_HERO_REQUEST_VIDEO_640'}))},context,research,designs,media);
const path='data/design/reference-application-v1/compositions.json',bytes=JSON.stringify(value,null,2)+'\n';
if(process.argv.includes('--record-session-revision')){if(await access(path).then(()=>true,()=>false))throw Error('B3_REFERENCE_APPLICATION_EXISTS');await mkdir('data/design/reference-application-v1',{recursive:true});await writeFile(path,bytes);}
else if(process.argv.includes('--verify')){if(await readFile(path,'utf8')!==bytes)throw Error('B3_REFERENCE_APPLICATION_REPLAY_MISMATCH');}
else throw Error('EXPLICIT_RECORD_OR_VERIFY_REQUIRED');
console.log(JSON.stringify({status:'PASS_REFERENCE_APPLICATION',application_sha256:inputSha256(value),variants:4,source_context:'PRESERVED',research_authority:value.authority,human_approval:value.human_approval}));
