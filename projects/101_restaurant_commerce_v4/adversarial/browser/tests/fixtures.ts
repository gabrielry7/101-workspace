import {test as base,expect,Page,APIRequestContext} from '@playwright/test';
import fs from 'node:fs';
import crypto from 'node:crypto';
export const config=JSON.parse(fs.readFileSync(process.env.COMMERCE_RUN_CONFIG!,'utf8'));
export const origin=new URL(config.base_url).origin;
if(!['127.0.0.1','localhost','[::1]'].includes(new URL(origin).hostname))throw new Error('Only loopback disposable targets are allowed');
export const businesses:string[]=config.business_ids || ['demo-restaurant-bogota'];
export const business=businesses[0];
export const root=(id=business)=>`/api/restaurants/${encodeURIComponent(id)}`;
export const operatorHeaders=config.single_staff_headers;
export const dualHeaders=config.dual_staff_headers;
export const unique=()=>crypto.randomUUID();
export const phone=()=>`30${String(crypto.randomInt(10000000,99999999))}`;
export const test=base.extend({
  context:async({context},use,testInfo)=>{
    const requests:any[]=[];
    await context.route('**/*',async route=>{
      const u=new URL(route.request().url());
      if(u.origin!==origin)throw new Error('Blocked non-target browser request: '+u.origin);
      await route.continue();
    });
    context.on('response',r=>requests.push({method:r.request().method(),url:r.url(),status:r.status()}));
    await use(context);
    await testInfo.attach('live-http-coverage.json',{body:Buffer.from(JSON.stringify(requests,null,2)),contentType:'application/json'});
  }
});
export {expect};
export async function item(request:APIRequestContext,id=business){
  const response=await request.get(root(id)+'/storefront');expect(response.status()).toBe(200);
  const store=await response.json();
  const product=store.menus.flatMap((m:any)=>m.categories).flatMap((c:any)=>c.items).find((i:any)=>i.available&&!i.modifier_groups.length);
  expect(product,'Seed must include available unmodified item').toBeTruthy();
  return {store,product};
}
export async function prepare(page:Page,request:APIRequestContext, name='Browser '+unique(), tel=phone()){
  const {product}=await item(request);
  await page.goto('/?business_id='+encodeURIComponent(business));
  await page.locator('#menu article').filter({has:page.getByRole('heading',{name:product.name,exact:true})}).getByRole('button').click();
  await expect(page.getByRole('button',{name:'Quitar',exact:true})).toBeVisible();
  await page.locator('#cName').fill(name);await page.locator('#cPhone').fill(tel);
  return {name,tel,product};
}
export async function body(request:APIRequestContext,id=business){
  const {store,product}=await item(request,id);
  return {customer:{name:'Browser '+unique(),phone:phone()},items:[{menu_item_id:product.id,quantity:1,modifiers:[]}],payment_provider:store.payment_provider,idempotency_key:unique()};
}
export async function create(request:APIRequestContext,id=business){
  const payload=await body(request,id);const r=await request.post(root(id)+'/orders',{data:payload});
  expect(r.status(),await r.text()).toBe(200);return await r.json();
}
export async function orderVisible(request:APIRequestContext,order:any){
  const r=await request.get('/api/orders/'+order.id,{headers:{'X-101-Order-Token':order.access_token}});
  expect(r.status()).toBe(200);expect((await r.json()).id).toBe(order.id);
  const staff=await request.get('/api/operator/restaurants/'+encodeURIComponent(business)+'/orders?limit=100',{headers:operatorHeaders});
  expect(staff.status()).toBe(200);expect((await staff.json()).some((o:any)=>o.id===order.id)).toBeTruthy();
}
