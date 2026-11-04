"""Chromium + real loopback app: WhatsApp campaign, inbound reply, opt-out and checkout."""
import json
import os
from pathlib import Path
from sqlalchemy import select
from test_campaign_browser import live_campaign, browser, playwright
from world_model.restaurant_commerce.campaign_demo import enable_whatsapp_demo, BUSINESS, PASSWORD
from world_model.restaurant_commerce.campaign_models import CampaignJob
from world_model.restaurant_commerce.models import Customer


def test_whatsapp_ui_inbox_and_existing_checkout(live_campaign):
    page,context,app,url,errors,external=live_campaign
    with app.state.session_factory() as s:
        app.state.campaign_options['integrations']['wa']=enable_whatsapp_demo(s,origin=url)
    page.goto('/campaigns')
    page.locator('#staffUsername').fill('campaign.manager');page.locator('#staffPassword').fill(PASSWORD);page.locator('#staffSignIn').click()
    playwright.expect(page.locator('#customers input')).to_have_count(7)
    page.locator('#channel').select_option('whatsapp');page.locator('#whatsappTemplate').select_option(index=1)
    page.locator('#save').click();playwright.expect(page.locator('#audienceSummary')).to_contain_text('3 elegibles')
    playwright.expect(page.frame_locator('#emailPreview').get_by_role('heading',name='WhatsApp · simulación')).to_be_visible()
    page.locator('#approve').click();playwright.expect(page.locator('#schedule')).to_be_enabled();page.locator('#schedule').click()
    playwright.expect(page.locator('#deliveries .delivery')).to_have_count(7)
    campaign=page.locator('#campaignSelect').input_value()
    page.goto('/whatsapp');playwright.expect(page.locator('#customer option')).to_have_count(7)
    with app.state.session_factory() as s:
        target=s.scalar(select(Customer).where(Customer.business_id==BUSINESS,Customer.email=='persona0@example.test')).id
    page.locator('#customer').select_option(target);page.locator('#inboundForm button').click()
    playwright.expect(page.locator('#conversations')).to_contain_text('Ventana de servicio abierta')
    page.locator('#conversations textarea').fill('Hola, el equipo te ayuda con la carta de prueba.')
    page.locator('#conversations button').click();playwright.expect(page.locator('#conversations')).to_contain_text('En cola')
    page.locator('#inboundText').fill('BAJA');page.locator('#inboundForm button').click()
    playwright.expect(page.locator('#conversations')).to_contain_text('Permiso retirado')
    page.locator('#dispatchReplies').click();playwright.expect(page.locator('#conversations')).to_contain_text('Omitida')
    output=Path(os.environ.get('WHATSAPP_BROWSER_EVIDENCE','/tmp/101-whatsapp-browser'));output.mkdir(parents=True,exist_ok=True)
    for width in [390,1440]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(output/f'whatsapp-inbox-{width}.png'),full_page=True)
    page.goto('/campaigns');playwright.expect(page.locator('#campaignSelect option')).to_have_count(2)
    page.locator('#campaignSelect').select_option(campaign)
    page.locator('#dispatch').click();playwright.expect(page.locator('.metric').filter(has_text='Aceptados por simulador').locator('strong')).to_have_text('2')
    page.locator('#receipt').click();playwright.expect(page.locator('.metric').filter(has_text='Entrega reportada').locator('strong')).to_have_text('2')
    page.screenshot(path=str(output/'whatsapp-campaign.png'),full_page=True)
    page.locator('#deliveries a').filter(has_text='Abrir enlace').first.click()
    playwright.expect(page.locator('#menu')).to_contain_text('Producto de prueba')
    page.locator('#menu article').filter(has_text='Producto de prueba').get_by_role('button').click()
    page.locator('#cName').fill('Cliente ficticio WhatsApp');page.locator('#cPhone').fill('3005550100')
    playwright.expect(page.locator('#checkoutButton')).to_be_enabled();page.locator('#checkoutButton').click()
    playwright.expect(page.locator('#checkoutRecovery')).to_contain_text('Pago confirmado')
    page.goto('/campaigns');playwright.expect(page.locator('#campaignSelect option')).to_have_count(2)
    page.locator('#campaignSelect').select_option(campaign)
    playwright.expect(page.locator('.metric').filter(has_text='Pedidos pagados atribuidos').locator('strong')).to_have_text('1')
    page.screenshot(path=str(output/'whatsapp-paid-report.png'),full_page=True)
    (output/'summary.json').write_text(json.dumps({'scope':'test','paid_orders':1,'captured_COP':24900,
        'opt_out_blocks_pending_campaign_and_reply':True,'widths':[390,1440],'page_errors':errors,'external_requests':external},indent=2))
