"""Actual HTTP + Chromium journey through the existing checkout and payment UI."""
import json
import os
import socket
import threading
import time
from pathlib import Path
import pytest
import uvicorn
from sqlalchemy import select
from test_browser_security import browser, playwright
from world_model.restaurant_commerce.campaign_demo import app_for_demo, BUSINESS, PASSWORD
from world_model.restaurant_commerce.models import Order, Payment, Customer
from world_model.restaurant_commerce.campaign_models import CampaignJob
from world_model.restaurant_commerce.security import sign_webhook


@pytest.fixture
def live_campaign(tmp_path,browser):
    sock=socket.socket();sock.bind(('127.0.0.1',0))
    url='http://127.0.0.1:'+str(sock.getsockname()[1])
    app=app_for_demo(f'sqlite:///{tmp_path / "campaign-browser.db"}',base_url=url)
    server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    for _ in range(100):
        if server.started:break
        time.sleep(.05)
    assert server.started
    context=browser.new_context(base_url=url,viewport={'width':1440,'height':1000})
    page=context.new_page();errors=[];external=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:external.append(r.url) if not r.url.startswith(url) else None)
    try:yield page,context,app,url,errors,external
    finally:
        context.close();server.should_exit=True;thread.join(timeout=10);sock.close()
        assert not thread.is_alive()
        assert not errors
        assert not external


def test_campaign_ui_through_checkout_and_refund(live_campaign):
    page,context,app,url,errors,external=live_campaign
    page.goto('/campaigns')
    page.locator('#staffUsername').fill('campaign.manager');page.locator('#staffPassword').fill(PASSWORD)
    page.locator('#staffSignIn').click()
    playwright.expect(page.locator('#customers input')).to_have_count(7)
    page.locator('#save').click()
    playwright.expect(page.locator('#audienceSummary')).to_contain_text('2 elegibles · 5 excluidos')
    playwright.expect(page.frame_locator('#emailPreview').get_by_role('heading',name='La mesa está puesta.')).to_be_visible()
    page.locator('#approve').click()
    playwright.expect(page.locator('#schedule')).to_be_enabled()
    page.locator('#schedule').click()
    playwright.expect(page.locator('#deliveries .delivery')).to_have_count(7)
    with app.state.session_factory() as s:
        customer=s.scalar(select(Customer).where(Customer.business_id==BUSINESS,Customer.email=='persona1@example.test'))
        pending=s.scalar(select(CampaignJob).where(CampaignJob.customer_id==customer.id))
        assert context.request.post('/campaign-unsubscribe/'+pending.unsubscribe_token).status==200
    page.locator('#dispatch').click()
    playwright.expect(page.locator('#deliveries')).to_contain_text('Baja confirmada')
    playwright.expect(page.locator('.metric').filter(has_text='Aceptados por simulador').locator('strong')).to_have_text('1')
    page.locator('#receipt').click()
    playwright.expect(page.locator('.metric').filter(has_text='Entrega reportada').locator('strong')).to_have_text('1')
    output=Path(os.environ.get('CAMPAIGN_BROWSER_EVIDENCE',str(Path('/tmp')/'101-campaign-browser')))
    output.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(output/'campaign-desktop.png'),full_page=True)
    page.locator('#deliveries a').filter(has_text='Abrir enlace').click()
    playwright.expect(page.locator('#menu')).to_contain_text('Producto de prueba')
    page.locator('#menu article').filter(has_text='Producto de prueba').get_by_role('button').click()
    page.locator('#cName').fill('Cliente ficticio');page.locator('#cPhone').fill('3005550100')
    playwright.expect(page.locator('#checkoutButton')).to_be_enabled()
    page.locator('#checkoutButton').click()
    playwright.expect(page.locator('#checkoutRecovery')).to_contain_text('Pago confirmado')
    with app.state.session_factory() as s:
        order=s.scalar(select(Order).where(Order.business_id==BUSINESS));payment=s.scalar(select(Payment).where(Payment.order_id==order.id))
        assert order.total_minor==24900 and order.payment_status=='paid'
        body=json.dumps({'event_id':'browser-refund','provider_reference':payment.provider_reference,
            'status':'partially_refunded','amount_minor':24900,'currency':'COP','refund_reference':'browser-refund-reference',
            'refund_amount_minor':5000}).encode()
    page.screenshot(path=str(output/'checkout-paid.png'),full_page=True)
    for _ in range(2):
        response=context.request.post('/api/webhooks/payments/simulated',data=body,
            headers={'X-101-Webhook-Signature':sign_webhook('synthetic-campaign-payment-secret',body),'Content-Type':'application/json'})
        assert response.status==200,response.text()
    page.goto('/campaigns')
    playwright.expect(page.locator('#campaignSelect option')).to_have_count(2)
    page.locator('#campaignSelect').select_option(index=1)
    playwright.expect(page.locator('.metric').filter(has_text='Pedidos pagados atribuidos').locator('strong')).to_have_text('1')
    playwright.expect(page.locator('.metric').filter(has_text='Ingresos netos').locator('strong')).to_have_text('19.900')
    page.screenshot(path=str(output/'campaign-report-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(output/'campaign-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    iframe=page.frame_locator('#emailPreview')
    assert iframe.locator('body').evaluate('(e)=>e.scrollWidth <= innerWidth')
    (output/'browser-evidence.json').write_text(json.dumps({'journey':'draft-preview-approve-schedule-unsubscribe-dispatch-delivery-click-checkout-paid-partial-refund-report',
        'paid_orders':1,'captured_COP':24900,'refunds_COP':5000,'net_COP':19900,'real_provider_calls':0,
        'page_errors':errors,'external_requests':external,'widths':[1440,390]},indent=2))
