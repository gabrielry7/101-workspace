import type {RenderObservation} from '../../composition/audit.ts';
// The browser bridge serializes object keys in a different order. The historical
// auditor compares JSON strings. Rebuild key order only; retain every observed value
// and array order, so missing/reordered/fabricated facts still fail its normal gates.
export function bindingObservation(o:RenderObservation):RenderObservation {
 return {...o,modules:o.modules.map(m=>({id:m.id,scope:m.scope,page:m.page,required:m.required,component:m.component,
  facts:m.facts.map(f=>({id:f.id,scope:f.scope,text:f.text})),offerings:m.offerings.map(f=>({id:f.id,scope:f.scope}))})),
  diagnostics:o.diagnostics.map(d=>({code:d.code,scope:d.scope,capability:d.capability,reason:d.reason})),
  exclusions:o.exclusions.map(e=>({id:e.id,scope:e.scope,reason:e.reason})),bindings:o.bindings.map(b=>({id:b.id,scope:b.scope,status:b.status})),
  navigation:o.navigation.map(n=>({page:n.page,href:n.href,current:n.current}))};
}
