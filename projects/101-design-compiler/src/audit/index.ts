export type IndexObservation={main_count:number;nested_main:boolean;h1_count:number;ax_main_count:number;skip_visible:boolean;skip_activated:boolean;skip_target_id:string;skip_target_is_main:boolean;link_reachable_by_tab:boolean;link_activated:boolean;link_href:string};
export function auditIndex(observed:IndexObservation){const codes:string[]=[];
 if(observed.main_count!==1||observed.nested_main||observed.ax_main_count!==1)codes.push('INDEX_MAIN_LANDMARK');
 if(observed.h1_count!==1)codes.push('INDEX_PRIMARY_HEADING');
 if(!observed.skip_visible||!observed.skip_activated||observed.skip_target_id!=='contenido'||!observed.skip_target_is_main)codes.push('INDEX_SKIP_LINK');
 if(!observed.link_reachable_by_tab||!observed.link_activated||!observed.link_href.startsWith('/h7/'))codes.push('INDEX_KEYBOARD_NAVIGATION');
 return {status:codes.length?'FAIL':'LAB_INDEX_PASS',codes,production_ready:false};
}
