/** Small visual primitives. Source evidence, layout selection and actions keep their existing owners. */
export const BONE_VERSION='101-bones-v1';
export const SURFACE_ROLES=Object.freeze(['panel','story','stage','intro','collection','track','card','brand','content','authorGroup','attribution','identity','avatar','photo','scrim','controls','footer','provider','dialog','dialogHeader','dialogBody','dialogFooter','empty']);
export const COLOR_ROLES=Object.freeze(['heading','intro','quote','author','date','action','stars','metric','provider','brand']);
export const SURFACE_PROPERTIES=Object.freeze({radius:'border-radius',fill:'background-color',borderWidth:'border-width',borderColor:'border-color',padding:'padding',gap:'gap',marginTop:'margin-top',marginBottom:'margin-bottom',shadow:'box-shadow',opacity:'opacity'});
const plain=v=>!!v&&Object.getPrototypeOf(v)===Object.prototype;
const keys=(value,allowed)=>{if(!plain(value)||Object.keys(value).some(k=>!allowed.includes(k)))throw Error('BONE_UNKNOWN_PROPERTY');};
const color=value=>{if(typeof value!=='string'||!/^#[a-f0-9]{6}$/i.test(value))throw Error('BONE_COLOR_REQUIRED');return value.toLowerCase();};
export function boneProfile(input={}){
 keys(input,['shape','avatar','surfaces','colors']);
 const {shape='recipe',avatar='recipe',surfaces={},colors={}}=input;
 if(!['recipe','square','soft','round'].includes(shape))throw Error('BONE_SHAPE');
 if(!['recipe','initials','hidden'].includes(avatar))throw Error('BONE_AVATAR');
 keys(surfaces,SURFACE_ROLES);keys(colors,COLOR_ROLES);
 const result={shape,avatar,surfaces:{},colors:{}};
 for(const [role,properties] of Object.entries(surfaces)){
  keys(properties,Object.keys(SURFACE_PROPERTIES));result.surfaces[role]={};
  for(const [key,value] of Object.entries(properties)){
   let normalized=value;
   if(['radius','borderWidth','padding','gap','marginTop','marginBottom'].includes(key)){
    if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>({radius:999,borderWidth:12,padding:96,gap:96,marginTop:128,marginBottom:128}[key]))throw Error('BONE_LENGTH');
   }else if(key==='opacity'){
    if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>1)throw Error('BONE_OPACITY');
   }else if(key==='shadow'){
    if(!['none','soft'].includes(value))throw Error('BONE_SHADOW');
   }else normalized=key==='fill'&&value==='transparent'?value:color(value);
   result.surfaces[role][key]=normalized;
  }
 }
 for(const [role,value] of Object.entries(colors))result.colors[role]=color(value);
 return result;
}
export const boneVariable=(role,key)=>`--bones-${role}-${key.replace(/[A-Z]/g,m=>'-'+m.toLowerCase())}`;
export function profileStyle(profile){
 const p=boneProfile(profile),values=[];
 for(const [role,properties] of Object.entries(p.surfaces))for(const [key,value] of Object.entries(properties)){
  const v=['radius','borderWidth','padding','gap','marginTop','marginBottom'].includes(key)?value+'px':key==='shadow'?(value==='none'?'none':'0 12px 30px #0002'):value;
  values.push(`${boneVariable(role,key)}:${v}`);
 }
 for(const [role,value] of Object.entries(p.colors))values.push(`--bones-color-${role}:${value}`);
 return values.join(';');
}
export function boneProfileAttributes(profile={}){
 const p=boneProfile(profile),edits=Object.entries(p.surfaces).flatMap(([r,v])=>Object.keys(v).map(k=>r+'.'+k));
 return `data-101-bones="${BONE_VERSION}" data-101-bones-shape="${p.shape}" data-101-bones-avatar="${p.avatar}" data-101-bone-edits="${edits.join(' ')}" data-101-bone-colors="${Object.keys(p.colors).join(' ')}"${profileStyle(p)?` style="${profileStyle(p)}"`:''}`;
}
export function applyBoneProfile(host,profile={}){
 const p=boneProfile(profile);
 for(const role of SURFACE_ROLES)for(const key of Object.keys(SURFACE_PROPERTIES))host.style.removeProperty(boneVariable(role,key));
 for(const role of COLOR_ROLES)host.style.removeProperty('--bones-color-'+role);
 host.dataset['101Bones']=BONE_VERSION;host.dataset['101BonesShape']=p.shape;host.dataset['101BonesAvatar']=p.avatar;
 host.dataset['101BoneEdits']=Object.entries(p.surfaces).flatMap(([r,v])=>Object.keys(v).map(k=>r+'.'+k)).join(' ');
 host.dataset['101BoneColors']=Object.keys(p.colors).join(' ');
 const declarations=profileStyle(p).split(';').filter(Boolean);
 for(const declaration of declarations){const i=declaration.indexOf(':');host.style.setProperty(declaration.slice(0,i),declaration.slice(i+1));}
 host.dispatchEvent(new host.ownerDocument.defaultView.CustomEvent('101:bones-change'));
 return p;
}
export function boneAttributes(kind,role){
 if(!['surface','media','layout','text','rating','divider'].includes(kind)||!SURFACE_ROLES.includes(role))throw Error('BONE_KIND_OR_ROLE');
 return `data-101-bone="${kind}" data-101-bone-role="${role}"`;
}
/** Trusted developer slot, just like the existing review composition parts. */
export function surface(role,children,{className='',tag='div',attributes=''}={}){
 if(!['div','section','header','figure','dialog','nav','footer','ol','p'].includes(tag)||!/^[A-Za-z0-9 _-]*$/.test(className)||typeof children!=='string')throw Error('BONE_SURFACE_MARKUP');
 return `<${tag} class="${className}" ${boneAttributes('surface',role)}${attributes?' '+attributes:''}>${children}</${tag}>`;
}
