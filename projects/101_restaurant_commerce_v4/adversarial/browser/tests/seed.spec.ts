import {test,expect,root} from './fixtures';
test('seed: actual deployed catalog is available',async({page,request})=>{
  const r=await request.get(root()+'/storefront');expect(r.status()).toBe(200);
  await page.goto('/');await expect(page.locator('#menu article').first()).toBeVisible();
});
