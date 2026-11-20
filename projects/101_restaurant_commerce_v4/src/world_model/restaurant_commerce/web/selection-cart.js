/** Preview selection only. Canonical commerce still owns SKUs, quotes and orders. */
export const CART_SCHEMA='101-selection-cart-v1';
/** Same-page controls ask the mounted cart owner; they never create another basket. */
export const CART_EVENTS=Object.freeze({request:'101:cart-state-request',state:'101:cart-state',open:'101:cart-open'});
export function cartLines(input,allowed){
 const ids=new Set(allowed);
 if(!input||input.schema!==CART_SCHEMA||!Array.isArray(input.lines))return [];
 const seen=new Set();return input.lines.slice(0,100).flatMap(line=>{
  if(!line||typeof line.productRef!=='string'||!ids.has(line.productRef)||seen.has(line.productRef)||!Number.isInteger(line.quantity)||line.quantity<1||line.quantity>99)return [];
  seen.add(line.productRef);return [{productRef:line.productRef,quantity:line.quantity}];
 });
}
export function changeQuantity(lines,productRef,quantity,allowed){
 if(!allowed.includes(productRef)||!Number.isInteger(quantity)||quantity<0||quantity>99)throw Error('CART_QUANTITY');
 const clean=cartLines({schema:CART_SCHEMA,lines},allowed);
 if(!quantity)return clean.filter(line=>line.productRef!==productRef);
 return clean.some(line=>line.productRef===productRef)?clean.map(line=>line.productRef===productRef?{productRef,quantity}:line):[...clean,{productRef,quantity}];
}
export function cartKey(businessRef){if(typeof businessRef!=='string'||!businessRef.trim())throw Error('CART_BUSINESS');return '101:selection-cart:'+encodeURIComponent(businessRef)+':v1';}
