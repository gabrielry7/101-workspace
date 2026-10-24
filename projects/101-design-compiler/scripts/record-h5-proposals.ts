// One-time recording of the structured art-direction output authored by the active Codex LLM session.
// This file is a recording utility, NOT an LLM call, generator or external API stub.
import { mkdir, writeFile } from 'node:fs/promises';
import { loadCompositionLab } from './load-composition-lab.ts';
import { contextHash, designContext } from '../src/design/search.ts';
import { ArtDirectionV1 } from '../src/design/contracts.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';
const lab=await loadCompositionLab(), hash=contextHash(lab);
const prompt=`H5 art-direction request, revision 1.\nUse the supplied frozen designContext as data. Propose three coherent directions with at least two page topologies per direction from Flow/Rail and Sequence/Split. Preserve every original route, module, fact, scope and H3 usage; no new claims, code, dependencies, assets, crop, image analysis, or media transformations. The original photographic description and existing H3 inspection are data, not permission for AI vision. References are unavailable: do not imply a researched corpus. Choose bounded tokens, quiet motion, explicit risks and rationale based on sparse content, branch separation and atmospheric-only media. Distinguish typographic sequence, dialogue and navigation-first directions. Return strict ArtDirectionV1 arrays; no business prose is rendered from these proposals. Search budget: 3 proposals, 24 cheap samples, 4 render slots. Existing session computation only; no provider API call or spend.\n`;
const common={schema_version:'1.0.0',context_sha256:hash,materiality:'unaltered-photograph',media_usage_ids:[lab.media.usage.id],motion:'quiet',
 constraints_acknowledged:{truth:true,rights:true,modules:true,no_code:true}};
const proposals=[
 {...common,id:'typographic-pause',principle:'La identidad verificada domina una secuencia editorial; el medio mantiene una pausa ambiental independiente.',dominance:'typography',
  rationale:'Dos hechos y una foto atmosférica permiten una jerarquía clara, no una promesa comercial. Separar identidad y oferta respeta el scope de sucursal. Flow/Sequence amplía la pausa; Rail/Sequence conserva la secuencia y hace explícito el índice lateral.',
  topologies:[{frame:'Flow',stage:'Sequence'},{frame:'Rail',stage:'Sequence'}],
  tokens:{palette:'olive',type:'serif',hierarchy:'monument',rhythm:'quiet',media_width:'inset',media_alignment:'center'},
  risks:['El contenido escaso puede parecer incompleto: mantener huecos y avisos visibles.','La imagen original supera el presupuesto habitual móvil y no admite derivados.','La diversidad móvil de secuencias es menor que en escritorio.']},
 {...common,id:'balanced-dialogue',principle:'Texto factual y fotografía ambiental dialogan en campos adyacentes, conservando lectura y crédito.',dominance:'dialogue',
  rationale:'Split relaciona identidad y atmósfera sin superponer texto ni atribuir el medio al negocio. Flow mantiene un índice horizontal; Rail/Split explora una topología anidada de navegación lateral y dos campos de contenido. En móvil ambos campos se apilan en orden lógico.',
  topologies:[{frame:'Flow',stage:'Split'},{frame:'Rail',stage:'Split'}],
  tokens:{palette:'earth',type:'serif',hierarchy:'compact',rhythm:'dense',media_width:'full',media_alignment:'end'},
  risks:['Rail/Split puede comprimir texto en tablet: reflow temprano a una columna.','La foto sigue siendo contexto genérico; no sirve como imagen documental de la oferta.','No forzar dos columnas donde falta medio: oferta ocupa ancho completo.']},
 {...common,id:'indexed-field',principle:'La navegación estructura un campo compacto con medio desplazado; la ausencia documental sigue explícita.',dominance:'navigation',
  rationale:'La separación entre página de identidad y oferta requiere orientación estable, no una plantilla de restaurante. Rail/Sequence prioriza índice y ritmo compacto; Flow/Split contrasta con campos horizontales. La tipografía sans enfatiza lectura del fixture, sin inferir posicionamiento de marca.',
  topologies:[{frame:'Rail',stage:'Sequence'},{frame:'Flow',stage:'Split'}],
  tokens:{palette:'ink',type:'sans',hierarchy:'compact',rhythm:'dense',media_width:'inset',media_alignment:'end'},
  risks:['No confundir indexación editorial con búsqueda de catálogo implementada.','La falta de referencias licenciadas limita la investigación estética.','Preferencia humana pendiente: ninguna dirección se declara ganadora.']},
].map(p=>ArtDirectionV1.parse(p));
const provenance={schema_version:'1.0.0',source:'ACTIVE_CODEX_SESSION_LLM',provider:'OpenAI / Codex session',
 model_family:'GPT-6 (provided by session instructions)',exact_model_id:null,model_id_status:'NOT_EXPOSED_TO_AGENT',
 actor:'/root/implementador',prompt_revision:'h5-art-direction-1',recorded_at:new Date().toISOString(),
 context_sha256:hash,prompt_sha256:inputSha256(prompt),output_sha256:inputSha256(proposals),
 invocation:'The active session LLM authored the three structured hypotheses in this recording utility after reading H2/H3/H4 and the frozen projected context. No separate API call.',
 tokens:null,cost:null,metering_status:'SESSION_METERING_NOT_AVAILABLE',new_provider_calls:0,new_spend:0,
 references_status:'MISSING',image_input:'NONE; existing H3 factual inspection metadata only',
 human_preference:'NOT_COLLECTED',replay:'Consume the recorded JSON; this recording utility is not rerun during search/build.'};
await mkdir('fixtures/design/h5',{recursive:true});
for(const [name,value] of Object.entries({'context.json':designContext(lab),'llm-output.json':proposals,'provenance.json':provenance}))
 await writeFile(`fixtures/design/h5/${name}`,JSON.stringify(value,null,2)+'\n');
await writeFile('fixtures/design/h5/prompt.txt',prompt);
console.log(JSON.stringify({context_sha256:hash,output_sha256:provenance.output_sha256,proposals:proposals.length,source:provenance.source}));
