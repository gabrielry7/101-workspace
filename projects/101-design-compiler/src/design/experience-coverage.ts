export function assertExperienceCoverage(views:{design:string;kind:string;viewport:{id:string;width:number;height:number}}[],profiles:readonly string[],pages:readonly string[],viewports:readonly {id:string;width:number;height:number}[]){
 const key=(design:string,kind:string,v:{id:string;width:number;height:number})=>`${design}/${kind}/${v.id}/${v.width}x${v.height}`;
 const expected=profiles.flatMap(id=>pages.flatMap(page=>viewports.map(v=>key(id,page,v)))).sort();
 const actual=views.map(v=>key(v.design,v.kind,v.viewport)).sort();
 if(JSON.stringify(actual)!==JSON.stringify(expected))throw Error('EXPERIENCE_VIEWPORT_COVERAGE_INVALID');
}
