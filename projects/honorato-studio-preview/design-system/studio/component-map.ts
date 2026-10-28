import registry from '../registry.json' with {type:'json'};
export const capabilities=[
 {id:'identity',label:'Recognize the business',inputs:['name','brand assets','positioning hypothesis'],fallback:'Name and source-backed bio'},
 {id:'navigation',label:'Find a page or section',inputs:['enabled routes','customer tasks'],fallback:'Native links; no empty destinations'},
 {id:'catalogue',label:'Explore products',inputs:['source-backed offering IDs','grouping interpretation'],fallback:'Text list; no invented price or stock'},
 {id:'filter',label:'Narrow the catalogue',inputs:['product names','categories','empty/reset states'],fallback:'Full list available without JavaScript'},
 {id:'detail',label:'Understand one product',inputs:['offering source','optional exact product image'],fallback:'Source-backed name and contact; no stock photo substitution'},
 {id:'gallery',label:'See products, people or process',inputs:['actual asset IDs','role','crop','source and permission'],fallback:'Omit unsupported photograph'},
 {id:'disclosure',label:'Read supporting detail',inputs:['label','content','keyboard/focus behavior'],fallback:'Native details or inline content'},
 {id:'visit',label:'Plan a visit or contact',inputs:['address','real contact destinations','hours conflicts'],fallback:'Existing channel link; omit unsupported booking'},
 {id:'motion',label:'Understand a transition',inputs:['purpose','trigger','interruption','reduced motion'],fallback:'Visible final state'},
 {id:'footer',label:'Find practical links',inputs:['business destinations','credits'],fallback:'Plain links'}
];
const rows:any[]=[
 ['shadcn/ui',['navigation','disclosure','gallery'],['apps/v4/registry/bases/base/ui/navigation-menu.tsx','apps/v4/registry/bases/base/ui/accordion.tsx','apps/v4/registry/bases/base/ui/carousel.tsx'],'React + selected Base/Radix primitives; Tailwind token/alias closure'],
 ['Base UI',['navigation','disclosure','filter'],['packages/react/src/navigation-menu/root/NavigationMenuRoot.tsx','packages/react/src/accordion/root/AccordionRoot.tsx','packages/react/src/combobox/root/ComboboxRoot.tsx'],'React headless primitives; shared contexts remain inside one island'],
 ['Radix Themes',['navigation','disclosure'],['packages/radix-ui-themes/src/components/dropdown-menu.tsx','packages/radix-ui-themes/src/components/tabs.tsx','packages/radix-ui-themes/src/components/dialog.tsx'],'React + Themes styles; styled components impose tokens'],
 ['HeroUI',['navigation','disclosure','filter'],['packages/react/src/components/menu/menu.tsx','packages/react/src/components/accordion/accordion.tsx','packages/react/src/components/tabs/tabs.tsx'],'React Aria + @heroui/styles; supported island required'],
 ['Origin / coss',['navigation'],['apps/origin/registry/default/components/comp-577.tsx'],'React + local button/navigation/popover/logo/utils + Radix, cva, Lucide; MIT applies to Origin directory'],
 ['Kibo UI',['gallery','filter','disclosure'],['packages/image-zoom/index.tsx','packages/combobox/index.tsx','packages/dialog-stack/index.tsx'],'React; image zoom uses react-medium-image-zoom; aliases/styles required'],
 ['Dice UI',['filter','disclosure'],['docs/registry/bases/base/ui/combobox.tsx','docs/registry/bases/base/ui/listbox.tsx','docs/registry/bases/base/ui/responsive-dialog.tsx'],'React + chosen Base/Radix dependency closure'],
 ['Animate UI',['disclosure','navigation','gallery','motion'],['packages/react/src/primitives/base-ui/accordion/accordion.tsx','packages/react/src/primitives/base-ui/navigation-menu/navigation-menu.tsx','packages/react/src/primitives/carousel/index.tsx'],'React19 + Motion14; MIT + Commons Clause at packages/react/LICENSE.md'],
 ['Cult UI',['gallery','footer'],['apps/www/registry/default/ui/minimal-card.tsx','apps/www/registry/default/ui/feature-carousel.tsx','apps/www/components/landing/feature-section.tsx','apps/www/components/landing/footer.tsx'],'React/Next imports; FeatureCarousel adds Motion and utility dependencies. FeatureSection/Footer are authored Cult site references, not generic catalogue logic'],
 ['Magic UI',['gallery','motion','disclosure'],['apps/www/registry/magicui/bento-grid.tsx','apps/www/registry/magicui/marquee.tsx','apps/www/registry/magicui/hero-video-dialog.tsx'],'React/Motion/Lucide as selected; decorative components do not supply business structure'],
 ['Aceternity UI',['gallery','motion'],[],'Hosted component source; exact item/version/terms must be acquired'],
 ['21st.dev',['navigation','gallery','motion'],[],'Discovery marketplace; author-specific source/license; not one component library'],
 ['FreeFrontend CSS loaders',['motion'],[],'Discovery of loading-state examples; exact source license needed; not a food menu']
];
export const componentMap={schema_version:'101-component-map-v1',purpose:'Route a customer task to an evidence contract and verified implementation source; not a gallery of interchangeable decorations',capabilities,
 components:[
 ...[
  ['gabo/catalogue','Grouped food catalogue',['catalogue','filter'],'MenuCollection.astro','catalogue-client.js','ReviewMenu.astro'],
  ['gabo/product-detail','Product detail and related links',['detail'],'DishDetail.astro',null,'StudioPage.astro'],
  ['gabo/navigation','Native responsive navigation',['navigation'],'ExperienceNavigation.astro',null,'Navigation.astro'],
 ].map(([id,name,roles,source,client,adapter])=>({id,name,kind:'component',capabilities:roles,framework:'Astro + browser-native JS',state:'adapted_in_studio',source_repository:'gabrielry7/101-workspace',revision:'d47576481ee60c0711e8d656e3c8824c66028a24',paths:['src/components/composition/'+source,...(client?['src/design/'+client]:[])],adapter:'src/studio/'+adapter,license:'Private shared upstream; preserve source notice, no general redistribution grant inferred',dependency_closure:['Astro'],adoption_reason:'Supplies actual restaurant catalogue and page behavior; replace synthetic fixtures with source-review evidence'})),
 ...rows.map(([name,roles,paths,dependencies])=>{
 const r:any=registry.resources.find(r=>r.name===name);
 return{id:name.toLowerCase().replace(/[^a-z0-9]+/g,'-'),name,kind:r.kind,capabilities:roles,framework:paths.length?'React':'item-specific',state:paths.length?'source_paths_verified_not_adopted':'discovery_only',source_url:r.url,revision:r.revision,paths,license:name==='Animate UI'?'MIT + Commons Clause; packages/react/LICENSE.md':r.license,dependency_closure:dependencies,adoption_reason:'Available alternative. Select for a concrete customer interaction and verify its full dependency/license closure before adoption.'};
 })],
 rules:['A UI action menu is not a restaurant catalogue','Component choice follows page purpose and evidence','Native Astro adapters and React islands share semantic token roles; no automatic stack migration','Unknown source path/license stays unknown','Brand composition can change while facts and functional contracts remain stable']};
export function selectComponents(capability:string,framework?:string){
 if(!capabilities.some(c=>c.id===capability))throw Error('UNKNOWN_CAPABILITY');
 return componentMap.components.filter(c=>(c.capabilities as string[]).includes(capability)&&(!framework||c.framework.includes(framework)));
}
