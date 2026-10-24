// Records proposals authored by this Codex session; not an API caller or simulated model runtime.
import { mkdir, writeFile } from 'node:fs/promises';
import { loadCohortLab } from './load-cohort-lab.ts';
import { designContext, contextHash } from '../src/design/search.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';
const concepts:Record<string,[string,string,string]>={
 hotel:['Silencio de catálogo','Habitaciones y comodidades separadas por ruta; título serif y espacio amplio sin sugerir fotografía del establecimiento.','Índice de alojamiento con navegación lateral explícita para comparar objetos declarados.'],
 dentista:['Lectura prudente','Servicios y perfiles tienen rutas distintas; jerarquía compacta y texto sobrio sin credenciales ni resultados supuestos.','Directorio lateral de información clínica ficticia; priorizar acceso visible a perfiles y límites.'],
 servicio:['Manual de cobertura','Separar catálogo de servicios y zona declarada; lectura directa sans y ritmo compacto para textos de alcance.','Registro lateral de servicios y cobertura; el índice no representa una solicitud funcional.'],
 hibrido:['Actividades coexistentes','Mantener membresías, calendario con fecha/zona y catálogo en rutas independientes; ningún objeto eclipsa al otro.','Archivo lateral de actividades coexistentes y productos; acortar títulos sin borrar fecha o timezone.'],
 'media-unknown':['Información sin imagen','El asset desconocido se conserva en inventario y se rechaza; contenido tipográfico sobrio sin sustituto visual.','Índice textual de un servicio sin fotografía elegible; restricción de derechos visible junto a trazabilidad.'],
};
const cohort=await loadCohortLab();
for(const c of cohort.cases){if(!c.lab)continue;const context=designContext(c.lab);const hash=contextHash(c.lab);const [name,a,b]=concepts[c.scenario]!;
 const prompt={role:'design-proposal',task:'Propose two distinct bounded art directions for this exact frozen synthetic business context. Preserve all semantic routes/modules/bindings and media permissions. No code, no invented content, no external images. Flow/Sequence versus Rail/Sequence; no photo dialog with absent media.',context_sha256:hash,context,limits:cohort.budget};
 const output=[a,b].map((rationale,i)=>({schema_version:'1.1.0',id:`${c.scenario}-${i?'indexed':'reading'}`,context_sha256:hash,principle:`${name}: ${i?'índice lateral visible':'lectura frontal'} sin medios elegibles.`,dominance:i?'navigation':'typography',materiality:'typography-only',rationale,topologies:[{frame:i?'Rail':'Flow',stage:'Sequence'}],tokens:{palette:c.scenario==='hotel'?'earth':c.scenario==='servicio'?'olive':'ink',type:i?'sans':c.scenario==='hotel'?'serif':'sans',hierarchy:i?'compact':'monument',rhythm:i?'dense':'quiet',media_width:'inset',media_alignment:'center'},media_usage_ids:[],motion:'quiet',risks:['No beauty calibration or human preference collected.','Typography-only materiality: no eligible image and no photograph is present.','Mobile reflow may collapse desktop structural distinction.'],constraints_acknowledged:{truth:true,rights:true,modules:true,no_code:true}}));
 const folder=`fixtures/cohort/h7/proposals/${c.scenario}`;await mkdir(folder,{recursive:true});
 const provenance={schema_version:'1.0.0',source:'REAL_CODEX_SESSION_AUTHORED_PROPOSALS',model_family:'GPT-6 (session developer identity)',exact_model_identifier:null,prompt_sha256:inputSha256(prompt),output_sha256:inputSha256(output),context_sha256:hash,tokens:null,cost:null,measured:false,provider_api_calls:0,new_spend:0,human_preference:'NOT_COLLECTED',materiality_contract:'ArtDirectionV1_1 1.1.0 typography-only; no photo present. Legacy ArtDirectionV1 unchanged.',not_api_runtime:true};
 for(const [file,value] of Object.entries({prompt,output,provenance,context}))await writeFile(`${folder}/${file}.json`,JSON.stringify(value,null,2)+'\n');
}
