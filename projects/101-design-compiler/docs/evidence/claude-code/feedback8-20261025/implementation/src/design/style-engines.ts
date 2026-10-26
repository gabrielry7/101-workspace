import{z}from'zod';
import type{DepthExperience}from'./depth-experience-contracts.ts';
export const StyleEngineV1=z.strictObject({id:z.string().regex(/^candidate-0[1-8]$/),label:z.string(),root:z.string().regex(/^\/b3\/candidate-0[1-8]\/$/),operator:z.enum(['ledger','front-page','ember','plate','market','marea','riso','indice']),role:z.enum(['general','artistic']),status:z.enum(['PRELIMINARY_ACCEPTED','AWAITING_HUMAN_REVIEW']),scope:z.literal('RESTAURANT_LAB')});
export const styleEngines=StyleEngineV1.array().length(8).parse([
 ['01','WhiteInk','ledger','general'],['02','Vermilion','front-page','general'],['03','Brasa','ember','artistic'],['04','Herbario','plate','artistic'],['05','Casa y patio','market','general'],['06','Cocina abierta','marea','general'],['07','Cartel duotono','riso','artistic'],['08','Hoja de contactos','indice','artistic']
].map(([n,label,operator,role],i)=>({id:'candidate-'+n,label,root:'/b3/candidate-'+n+'/',operator,role,status:i<4?'PRELIMINARY_ACCEPTED':'AWAITING_HUMAN_REVIEW',scope:'RESTAURANT_LAB'})));
if(new Set(styleEngines.map(e=>e.id)).size!==8||new Set(styleEngines.map(e=>e.operator)).size!==8)throw Error('ENGINE_REGISTRY_NOT_UNIQUE');
export type StyleEngine=z.infer<typeof StyleEngineV1>;
export type EngineProfile=Omit<DepthExperience['profiles'][number],'id'>&{id:string};
export function engineForProfile(id:string){return styleEngines.find(e=>e.id===id&&Number(e.id.slice(-2))>4)}
export function newEngineProfiles(lab:{site:DepthExperience}):EngineProfile[]{return styleEngines.slice(4).map(e=>({...lab.site.profiles[0],id:e.id,root:e.root,label:e.label,references:[],rationale:e.role==='general'?'Motor de uso general: composición y tipografía propias sobre los módulos compartidos.':'Motor artístico: composición experimental sobre los mismos datos y funciones compartidas.',design_status:'REPLACEMENT_AWAITING_HUMAN_REVIEW'}))}
