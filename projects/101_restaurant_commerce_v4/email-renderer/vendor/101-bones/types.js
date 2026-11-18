/** Semantic categories/types are separate from renderer kind, CSS appearance and brand coat. */
export const BONE_CATEGORIES=Object.freeze({
 surface:{label:'Superficies',types:['container','media-frame','button-surface']},
 layout:{label:'Distribución',types:['form','section','stack','action-group','spacing','position']},
 text:{label:'Texto',types:['heading','body','field-label','button-label','input-value','placeholder','feedback']},
 button:{label:'Botones',types:['primary','secondary','icon','trigger']},
 link:{label:'Enlaces',types:['policy','product','navigation','contact']},
 field:{label:'Campos',types:['email','one-time-code','search','checkbox']},
 media:{label:'Medios',types:['image','video','logo','vector']},
 icon:{label:'Iconos',types:['frame','glyph']},
 decoration:{label:'Bordes y efectos',types:['border','shadow','focus-outline','backdrop','hover-state','active-state','motion','mask']},
});
export function validateBoneAnatomy(definitions){
 const roles=new Set();
 for(const d of definitions){
  if(!d.role||roles.has(d.role))throw Error('BONE_ROLE_DUPLICATE');roles.add(d.role);
  if(!BONE_CATEGORIES[d.category]?.types.includes(d.type))throw Error('BONE_CATEGORY_TYPE');
  if(!d.source||!['new','reused'].includes(d.status)||typeof d.selector!=='string')throw Error('BONE_OWNER');
  if(d.category==='text'&&(!d.hierarchy?.group||!Number.isInteger(d.hierarchy.level)||d.hierarchy.level<1||d.hierarchy.level>4))throw Error('BONE_TEXT_HIERARCHY');
 }
 for(const d of definitions){
  if(d.parent!==null&&!roles.has(d.parent))throw Error('BONE_PARENT');
  for(const r of d.relations||[])if(!['labels','explains','decorates','fills','submits','dismisses','opens','feedback-for'].includes(r.kind)||!roles.has(r.target))throw Error('BONE_RELATION');
  const seen=new Set([d.role]);let parent=d.parent;
  while(parent!==null){if(seen.has(parent))throw Error('BONE_PARENT_CYCLE');seen.add(parent);parent=definitions.find(p=>p.role===parent).parent;}
 }
 return definitions;
}
