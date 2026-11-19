export type CheckoutProfile = {schema_version:"1";layout:"sidebar"|"stacked";geometry:Record<string,number>;typography:Record<string,number|string>;colors:Record<string,string>;bones:{surfaces:Record<string,Record<string,number|string>>}};
export const contract: {presets:Record<string,CheckoutProfile>;geometry:Record<string,[number,number]>;typography:Record<string,[number,number]>;surfaces:string[];colors:string[];fonts:Record<string,string>};
export const CHECKOUT_ANATOMY: {role:string;category:string;type:string;selector:string;parent:string|null;status:string;source:string;kind:string;id:string}[];
export function checkoutProfile(input:unknown):CheckoutProfile;
export function preset(name:string):CheckoutProfile;
export function applyCheckoutProfile(host:HTMLElement,input:unknown):CheckoutProfile;
