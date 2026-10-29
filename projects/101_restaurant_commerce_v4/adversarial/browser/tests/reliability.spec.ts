// spec: specs/adversarial.md
// seed: tests/seed.spec.ts
import {test,expect,prepare,root,body,create,orderVisible,businesses,business,operatorHeaders,dualHeaders,unique,phone} from './fixtures';

test('successful live customer order is retrievable and visible to staff',async({page,request})=>{
  await prepare(page,request);
  const waiting=page.waitForResponse(r=>new URL(r.url()).pathname===root()+'/orders'&&r.request().method()==='POST');
  await page.locator('#checkoutButton').click();const r=await waiting;expect(r.status(),await r.text()).toBe(200);
  await orderVisible(request,await r.json());
});

test('double clicks while real response is delayed send one checkout',async({page,request})=>{
  let posts=0;let captured:any;
  await page.route('**'+root()+'/orders',async route=>{posts++;const response=await route.fetch({maxRedirects:0});captured=await response.json();await new Promise(r=>setTimeout(r,350));await route.fulfill({response});});
  await prepare(page,request);await page.locator('#checkoutButton').evaluate((e:HTMLButtonElement)=>{e.click();e.click();});
  await expect.poll(()=>captured?.id).toBeTruthy();await expect(page.locator('#checkoutButton')).toBeEnabled();
  expect(posts).toBe(1);await orderVisible(request,captured);
});

test('lost response after real commit retries identical request and order',async({page,request})=>{
  let first:any;const bodies:any[]=[];
  await page.route('**'+root()+'/orders',async route=>{
    bodies.push(route.request().postDataJSON());
    if(bodies.length===1){const response=await route.fetch({maxRedirects:0});expect(response.status()).toBe(200);first=await response.json();await route.abort('failed');}
    else await route.continue();
  });
  await prepare(page,request);await page.locator('#checkoutButton').click();
  await expect(page.locator('#notice')).toContainText('Reintenta');
  const waiting=page.waitForResponse(r=>new URL(r.url()).pathname===root()+'/orders');
  await page.locator('#checkoutButton').click();const response=await waiting;expect(response.status()).toBe(200);
  expect((await response.json()).id).toBe(first.id);expect(bodies.length).toBe(2);expect(bodies[1]).toEqual(bodies[0]);
  await orderVisible(request,first);
});

test('same checkout intent submitted concurrently in two real tabs recovers one order',async({context,request})=>{
  const payload=await body(request);const pages=await Promise.all([context.newPage(),context.newPage()]);
  await Promise.all(pages.map(p=>p.goto('/')));
  const results=await Promise.all(pages.map(p=>p.evaluate(async({url,payload})=>{const r=await fetch(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});return {status:r.status,body:await r.json()};},{url:root()+'/orders',payload})));
  expect(results.every(r=>[200,409].includes(r.status))).toBeTruthy();
  const successes=results.filter(r=>r.status===200);expect(successes.length).toBeGreaterThan(0);
  expect(new Set(successes.map(r=>r.body.id)).size).toBe(1);
  const replay=await request.post(root()+'/orders',{data:payload});expect(replay.status()).toBe(200);expect((await replay.json()).id).toBe(successes[0].body.id);
});

test('reload after committed lost response must recover same order',async({page,request},testInfo)=>{
  let first:any;let intercepted=false;const submitted:any[]=[];
  await page.route('**'+root()+'/orders',async route=>{
    submitted.push(route.request().postDataJSON());
    if(!intercepted){intercepted=true;const response=await route.fetch({maxRedirects:0});expect(response.status()).toBe(200);first=await response.json();await route.abort('failed');}
    else await route.continue();
  });
  const customer=await prepare(page,request);await page.locator('#checkoutButton').click();
  await expect(page.locator('#notice')).toContainText('Reintenta');
  const saved=await page.evaluate(()=>Object.entries(localStorage).find(([key])=>key.startsWith('101.checkout.v1:'))?.[1]);
  expect(saved).toBeTruthy();expect(saved).not.toContain(customer.name);expect(saved).not.toContain(customer.tel);
  const recovery=page.waitForResponse(r=>new URL(r.url()).pathname===root()+'/orders/recover');
  await page.reload();const response=await recovery;expect(response.status()).toBe(200);const second=await response.json();
  await expect(page.locator('#checkoutRecovery')).toContainText(first.public_code);
  // Recovery is a read of the original durable intent, never a second order submission.
  expect(submitted.length).toBe(1);expect(second.id).toBe(first.id);
  await expect(page.locator('#cName')).toHaveValue('');
  await testInfo.attach('reload-order-evidence.json',{body:Buffer.from(JSON.stringify({first_order:first.id,recovered_order:second.id,order_posts:submitted.length,stored_keys:Object.keys(JSON.parse(saved!))})),contentType:'application/json'});
  await orderVisible(request,second);
});

test('offline submission then reconnect retries the same intent',async({page,context,request})=>{
  await prepare(page,request);const bodies:any[]=[];
  page.on('request',r=>{if(new URL(r.url()).pathname===root()+'/orders')bodies.push(r.postDataJSON());});
  await context.setOffline(true);await page.locator('#checkoutButton').click();await expect(page.locator('#notice')).toContainText('Reintenta');
  await context.setOffline(false);
  const waiting=page.waitForResponse(r=>new URL(r.url()).pathname===root()+'/orders');await page.locator('#checkoutButton').click();
  const response=await waiting;expect(response.status()).toBe(200);expect(bodies.length).toBe(2);expect(bodies[1]).toEqual(bodies[0]);await orderVisible(request,await response.json());
});

test('stale real food quote cannot resurrect an empty cart',async({page,request})=>{
  let release!:()=>void;let fetched=false;const gate=new Promise<void>(r=>release=r);
  await page.route('**'+root()+'/orders/quote',async route=>{const response=await route.fetch({maxRedirects:0});fetched=true;await gate;await route.fulfill({response});});
  await prepare(page,request);await expect.poll(()=>fetched).toBeTruthy();await page.getByRole('button',{name:'Quitar',exact:true}).click();release();
  await page.waitForTimeout(200);expect((await page.locator('#cartTotal').innerText()).replace(/\D/g,'')).toBe('0');
});

test('changed address rejects delayed genuine delivery quote',async({page,request})=>{
  let release!:()=>void;let fetched=false;const gate=new Promise<void>(r=>release=r);let orderPosts=0;
  page.on('request',r=>{if(new URL(r.url()).pathname===root()+'/orders')orderPosts++;});
  await page.route('**'+root()+'/delivery/quote',async route=>{const response=await route.fetch({maxRedirects:0});expect(response.status()).toBe(200);fetched=true;await gate;await route.fulfill({response});});
  await prepare(page,request);await page.locator('#deliveryBtn').click();await page.locator('#dAddress').fill('Synthetic Address A');await page.locator('#dLat').fill('4.6697');await page.locator('#dLng').fill('-74.0549');
  await page.getByRole('button',{name:'Cotizar domicilio',exact:true}).click();await expect.poll(()=>fetched).toBeTruthy();await page.locator('#dAddress').fill('Synthetic Address B');release();await page.waitForTimeout(150);
  await page.locator('#checkoutButton').click();await expect(page.locator('#notice')).toContainText('Cotiza el domicilio');expect(orderPosts).toBe(0);
});

test('denied browser storage and missing randomUUID preserve checkout',async({page,request})=>{
  await page.addInitScript(()=>{for(const name of ['localStorage','sessionStorage'])Object.defineProperty(window,name,{get(){throw new DOMException('blocked','SecurityError')}});Object.defineProperty(crypto,'randomUUID',{value:undefined});});
  await prepare(page,request);const waiting=page.waitForResponse(r=>new URL(r.url()).pathname===root()+'/orders');await page.locator('#checkoutButton').click();const response=await waiting;expect(response.status()).toBe(200);await orderVisible(request,await response.json());
});

test('switching businesses discards delayed authorized staff response',async({page,request})=>{
  expect(businesses.length,'Two real seed businesses are required').toBeGreaterThan(1);
  const oldOrder=await create(request);let release!:()=>void;let fetched=false;const gate=new Promise<void>(r=>release=r);
  await page.context().addCookies([{name:'commerce_staff',value:dualHeaders.Cookie.split('=')[1],url:(await import('./fixtures')).origin,httpOnly:true,sameSite:'Strict'}]);
  await page.goto('/admin');await expect(page.locator('#staffStatus')).toContainText('synthetic.dual');
  await page.route('**/api/operator/restaurants/'+business+'/orders',async route=>{const response=await route.fetch({maxRedirects:0});expect(response.status()).toBe(200);fetched=true;await gate;await route.fulfill({response});});
  await page.getByRole('button',{name:'Actualizar',exact:true}).click();await expect.poll(()=>fetched).toBeTruthy();await page.locator('#business').fill(businesses[1]);release();await page.waitForTimeout(200);
  await expect(page.locator('#orders')).not.toContainText(oldOrder.public_code);
  await page.unroute('**/api/operator/restaurants/'+business+'/orders');
  const fresh=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/operator/restaurants/'+businesses[1]+'/orders'&&r.status()===200);
  await page.getByRole('button',{name:'Actualizar',exact:true}).click();await fresh;
});

test('staff authority must be scoped to one business',async({request},testInfo)=>{
  expect(businesses.length).toBeGreaterThan(1);
  const own=await request.get('/api/operator/restaurants/'+business+'/orders',{headers:operatorHeaders});expect(own.status()).toBe(200);
  const other=await request.get('/api/operator/restaurants/'+businesses[1]+'/orders',{headers:operatorHeaders});
  await testInfo.attach('staff-scope-evidence.json',{body:Buffer.from(JSON.stringify({own_status:own.status(),other_business_status:other.status(),authority_model:'HTTP-issued named staff session with one explicit membership'})),contentType:'application/json'});
  expect(other.status(),'Single-business staff must not access another business').toBe(403);
});

test('named staff login survives reload without browser storage; logout removes access',async({page})=>{
  const {config}=await import('./fixtures');
  await page.addInitScript(()=>{for(const name of ['localStorage','sessionStorage'])Object.defineProperty(window,name,{get(){throw new DOMException('blocked','SecurityError')}});});
  await page.goto('/admin');
  await page.locator('#staffUsername').fill('synthetic.single');
  await page.locator('#staffPassword').fill(config.staff_password);
  await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();
  await expect(page.locator('#staffStatus')).toContainText('synthetic.single');
  await page.reload();
  await expect(page.locator('#staffStatus')).toContainText('synthetic.single');
  expect(await page.locator('#staffPassword').inputValue()).toBe('');
  expect(await page.evaluate(()=>document.cookie)).not.toContain('commerce_staff');
  await page.getByRole('button',{name:'Cerrar sesión',exact:true}).click();
  await expect(page.locator('#staffLogin')).toBeVisible();
  await expect(page.locator('#orders')).toContainText('Actualizar para cargar datos autorizados.');
  await page.reload();
  await expect(page.locator('#staffLogin')).toBeVisible();
});

test('delayed session restore cannot republish staff after logout',async({page})=>{
  const {config}=await import('./fixtures');
  const login=await page.request.post('/api/staff/login',{data:{username:'synthetic.single',password:config.staff_password},headers:{'X-101-Login':'1'}});
  expect(login.status()).toBe(200); // This logout test owns its session; never revoke a shared harness credential.
  await page.goto('/admin');await expect(page.locator('#staffStatus')).toContainText('synthetic.single');
  let release!:()=>void;const gate=new Promise<void>(r=>release=r);let fetched=false;
  await page.route('**/api/staff/me',async route=>{const response=await route.fetch();expect(response.status()).toBe(200);fetched=true;await gate;await route.fulfill({response});});
  await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
  await expect.poll(()=>fetched).toBeTruthy();
  await page.getByRole('button',{name:'Cerrar sesión',exact:true}).click();
  await expect(page.locator('#staffLogin')).toBeVisible();release();
  await page.waitForTimeout(250);
  await expect(page.locator('#staffStatus')).not.toContainText('synthetic.single');
});

test('staff session deadline includes a stalled response body',async({page})=>{
  const {config}=await import('./fixtures');
  const login=await page.request.post('/api/staff/login',{data:{username:'synthetic.single',password:config.staff_password},headers:{'X-101-Login':'1'}});
  expect(login.status()).toBe(200);
  await page.addInitScript(()=>{
    const original=window.fetch;
    window.fetch=async(url,options={})=>{
      const response=await original(url,options);
      if(String(url)==='/api/staff/me'){
        const json=response.json.bind(response);
        response.json=async()=>{await json();return new Promise((_resolve,reject)=>{
          options.signal!.addEventListener('abort',()=>reject(new DOMException('Controlled stalled body','AbortError')),{once:true});
        });};
      }
      return response;
    };
  });
  await page.goto('/admin');
  await expect(page.locator('#staffStatus')).toContainText('Sin conexión',{timeout:20000});
  await expect(page.locator('#staffLogin')).toBeVisible();
});
