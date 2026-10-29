// spec: specs/official-agent-plan.md
// seed: tests/seed.spec.ts
import {test,expect} from './fixtures';
test.describe('Live catalog and adversarial checkout',()=>{
  test('catalog cart text remains available',async({page})=>{
    // Open the live seeded catalog.
    await page.goto('/');
    // Click Agregar for Papas de la casa.
    await page.locator('#menu article').filter({has:page.getByRole('heading',{name:'Papas de la casa',exact:true})}).getByRole('button').click();
    // Verify the actual product is shown in the cart without placing an order.
    await expect(page.locator('#cartRows')).toContainText('1 × Papas de la casa');
  });
});
