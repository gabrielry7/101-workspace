"""Actual browser: SMS preview, permission withdrawal, shared checkout and report."""
import json
import os
from pathlib import Path
from sqlalchemy import select
from test_campaign_browser import live_campaign,browser,playwright
from world_model.restaurant_commerce.campaign_demo import enable_sms_demo,BUSINESS,PASSWORD
from world_model.restaurant_commerce.models import Customer


def test_sms_ui_optout_and_canonical_checkout(live_campaign):
    page,context,app,url,errors,external=live_campaign
    with app.state.session_factory() as s:app.state.campaign_options['integrations']['honorato-sms-test']=enable_sms_demo(s,origin=url)
    page.goto('/campaigns');page.locator('#staffUsername').fill('campaign.manager');page.locator('#staffPassword').fill(PASSWORD);page.locator('#staffSignIn').click()
    playwright.expect(page.locator('#customers input')).to_have_count(7)
    page.locator('#channel').select_option('sms');page.locator('#body').fill('Hola {name}. Mensaje de prueba, sin oferta real.')
    page.locator('#save').click();playwright.expect(page.locator('#audienceSummary')).to_contain_text('3 elegibles')
    playwright.expect(page.locator('#smsEstimate')).to_contain_text('segmentos')
    playwright.expect(page.frame_locator('#emailPreview').get_by_role('heading',name='SMS · simulación')).to_be_visible()
    campaign=page.locator('#campaignSelect').input_value()
    page.locator('#approve').click();playwright.expect(page.locator('#schedule')).to_be_enabled();page.locator('#schedule').click()
    playwright.expect(page.locator('#deliveries .delivery')).to_have_count(7)
    page.goto('/sms');playwright.expect(page.locator('#customer option')).to_have_count(7)
    with app.state.session_factory() as s:cid=s.scalar(select(Customer).where(Customer.business_id==BUSINESS,Customer.email=='persona0@example.test')).id
    page.locator('#customer').select_option(cid);page.locator('#inboundForm button').click()
    playwright.expect(page.locator('#inbound')).to_contain_text('BAJA')
    out=Path(os.environ.get('SMS_BROWSER_EVIDENCE','/tmp/101-sms-browser'));out.mkdir(parents=True,exist_ok=True)
    audit=[]
    for width in [390,1440]:
        page.set_viewport_size({'width':width,'height':1000});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        axe=os.environ.get('COMMERCE_AXE_PATH')
        if axe:
            page.evaluate(Path(axe).read_text());results=page.evaluate('async()=>await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})')
            audit.append({'width':width,'violations':[v['id'] for v in results['violations']]});assert not results['violations']
        page.screenshot(path=str(out/f'sms-{width}.png'),full_page=True)
    page.goto('/campaigns');playwright.expect(page.locator('#campaignSelect option')).to_have_count(2);page.locator('#campaignSelect').select_option(campaign)
    page.locator('#dispatch').click();playwright.expect(page.locator('.metric').filter(has_text='Aceptados por simulador').locator('strong')).to_have_text('2')
    page.locator('#receipt').click();playwright.expect(page.locator('.metric').filter(has_text='Entrega reportada').locator('strong')).to_have_text('2')
    page.locator('#deliveries a').filter(has_text='Abrir enlace').first.click()
    playwright.expect(page.locator('#menu')).to_contain_text('Producto de prueba')
    page.locator('#menu article').filter(has_text='Producto de prueba').get_by_role('button').click()
    page.locator('#cName').fill('Cliente ficticio SMS');page.locator('#cPhone').fill('3005550100')
    playwright.expect(page.locator('#checkoutButton')).to_be_enabled();page.locator('#checkoutButton').click()
    playwright.expect(page.locator('#checkoutRecovery')).to_contain_text('Pago confirmado')
    page.goto('/campaigns');playwright.expect(page.locator('#campaignSelect option')).to_have_count(2);page.locator('#campaignSelect').select_option(campaign)
    playwright.expect(page.locator('.metric').filter(has_text='Pedidos pagados atribuidos').locator('strong')).to_have_text('1')
    page.locator('#testConsent').fill('synthetic owner test permission');page.locator('#prepareTest').click()
    playwright.expect(page.locator('#testReview')).to_contain_text('Sin envío autorizado')
    page.screenshot(path=str(out/'sms-paid-report.png'),full_page=True)
    (out/'summary.json').write_text(json.dumps({'scope':'test','paid_orders':1,'captured_COP':24900,'opt_out_blocked':True,
        'test_review_authorizes_no_send':True,'page_errors':errors,'external_requests':external,'accessibility':audit},indent=2)+'\n')
