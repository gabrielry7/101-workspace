export function allowBackgroundMotion(p:{reducedMotion:boolean;saveData:boolean;documentVisible:boolean;inView:boolean;manualPause:boolean}){
 return !p.reducedMotion&&!p.saveData&&p.documentVisible&&p.inView&&!p.manualPause;
}
