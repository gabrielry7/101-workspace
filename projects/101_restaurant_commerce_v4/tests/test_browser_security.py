from staff_helpers import staff_headers
"""M1 regression proof against real FastAPI responses; no external provider traffic.

Run with browser extra installed and COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium
(or install Playwright Chromium). Browser tests must run explicitly in release CI.
"""
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from world_model.restaurant_commerce.api import create_app

playwright = pytest.importorskip('playwright.sync_api')
PAYLOAD = '<img src=x onerror="window.auditXss=true">\' & <script>window.auditXss=true</script>'


@pytest.fixture(scope='module')
def browser():
    with playwright.sync_playwright() as p:
        executable = os.environ.get('COMMERCE_BROWSER_EXECUTABLE')
        browser = p.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
        yield browser
        browser.close()


@pytest.fixture
def site(tmp_path, browser):
    app = create_app(database_url=f'sqlite:///{tmp_path / "browser.db"}', seed=True,
                     checkout_url_origins=('https://checkout.example.test',),
                     tracking_url_origins=('https://tracking.example.test',))
    with TestClient(app) as client:
        staff_headers(client)
        context = browser.new_context()
        context.add_cookies([{'name':'commerce_staff','value':client.cookies['commerce_staff'],'url':'http://commerce.test','httpOnly':True,'sameSite':'Strict'}])
        page = context.new_page()
        overrides, requests, errors, external = {}, [], [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        def route(r):
            req = r.request
            parsed = urlsplit(req.url)
            if parsed.netloc != 'commerce.test':
                external.append(req.url)
                return r.abort()
            path = parsed.path + ('?' + parsed.query if parsed.query else '')
            requests.append((req.method, path, req.post_data))
            if parsed.path in overrides:
                body = overrides[parsed.path]
                return r.fulfill(status=200, json=body)
            headers = {k: v for k, v in req.headers.items() if k in ('content-type', 'cookie', 'x-101-csrf', 'x-101-login', 'x-101-order-token')}
            response = client.request(req.method, path, content=req.post_data_buffer, headers=headers)
            # httpx has decoded gzip; do not forward stale content encoding/length.
            hdr = {k: v for k, v in response.headers.items() if k not in ('content-encoding','content-length')}
            r.fulfill(status=response.status_code, body=response.content, headers=hdr)
        context.route('**/*', route)
        yield page, client, overrides, requests, errors, external
        context.close()


def cart(client):
    store = client.get('/api/restaurants/demo-restaurant-bogota/storefront').json()
    item = next(i for m in store['menus'] for c in m['categories'] for i in c['items'] if i['name'] == 'Smash 101')
    selections = [{'group_id': g['id'], 'option_ids': [g['options'][0]['id']]} for g in item['modifier_groups'] if g['required']]
    return [{'menu_item_id': item['id'], 'quantity': 1, 'modifiers': selections}]


def order(client, **extra):
    response = client.post('/api/restaurants/demo-restaurant-bogota/orders', json={
        'customer': {'name': PAYLOAD, 'phone': '3005550101'}, 'items': cart(client),
        'idempotency_key': 'browser-order', **extra})
    assert response.status_code == 200, response.text
    return response.json()


def assert_safe(page, errors, external):
    assert page.evaluate('window.auditXss !== true')
    assert page.locator('img[src="x"]').count() == 0
    assert not errors
    assert not external
    assert page.locator('[onclick], [oninput], [onerror], script:not([src])').count() == 0


def test_public_input_to_staff_render_and_actions(site):
    page, client, _, requests, errors, external = site
    o = order(client)
    assert client.post(f'/api/payments/simulated/{o["payments"][0]["provider_reference"]}/complete').status_code == 200
    when = (datetime.now(timezone.utc) + timedelta(days=2)).replace(hour=12, minute=0, second=0, microsecond=0)
    r = client.post('/api/restaurants/demo-restaurant-bogota/reservations', json={
        'customer': {'name': PAYLOAD, 'phone': '3005550102'}, 'starts_at': when.isoformat(), 'party_size': 2})
    assert r.status_code == 200, r.text
    page.goto('https://commerce.test/admin')
    page.get_by_role('button', name='Aceptar', exact=True).wait_for()
    assert PAYLOAD in page.locator('#orders').inner_text()
    assert PAYLOAD in page.locator('#reservations').inner_text()
    assert_safe(page, errors, external)
    assert not any(method == 'PATCH' for method, _, _ in requests)
    page.get_by_role('button', name='Aceptar', exact=True).click()
    page.get_by_role('button', name='Preparar', exact=True).wait_for()
    page.get_by_role('button', name='Confirmar', exact=True).click()
    playwright.expect(page.locator("#reservations .status")).to_have_text("confirmed")
    assert_safe(page, errors, external)


def test_storefront_catalog_modifiers_cart_and_errors(site):
    page, client, overrides, _, errors, external = site
    url='/api/restaurants/demo-restaurant-bogota/storefront'
    store=client.get(url).json()
    item=next(i for m in store['menus'] for c in m['categories'] for i in c['items'] if i['name']=='Smash 101')
    store['display_name']=PAYLOAD
    store['menus'][0]['categories'][0]['name']=PAYLOAD
    item['name']=PAYLOAD; item['description']=PAYLOAD
    for g in item['modifier_groups']:
        g['name']=PAYLOAD
        for option in g['options']: option['name']=PAYLOAD
    overrides[url]=store
    page.goto('https://commerce.test/')
    page.locator('#menu article').first.wait_for()
    article=page.locator('#menu article').filter(has_text=PAYLOAD).first
    article.get_by_role('button').click()
    page.locator('#itemDialog[open]').wait_for()
    # Required group validation used to interpolate the hostile group name in notice HTML.
    page.get_by_role('button',name='Agregar al pedido',exact=True).click()
    assert PAYLOAD in page.locator('#notice').inner_text()
    assert_safe(page, errors, external)
    for group in page.locator('#modifierGroups .modifier').all():
        group.locator('input').first.check()
    page.get_by_role('button',name='Agregar al pedido',exact=True).click()
    page.get_by_role('button',name='Quitar',exact=True).wait_for()
    assert PAYLOAD in page.locator('#cartRows').inner_text()
    page.get_by_role('button',name='Quitar',exact=True).click()
    assert page.get_by_role('button',name='Quitar',exact=True).count()==0
    assert_safe(page, errors, external)


def test_delivery_fields_urls_and_action_closures(site):
    page, _, overrides, requests, errors, external=site
    id="id'\"/><img src=x onerror=window.auditXss=true>"
    overrides['/api/operator/restaurants/demo-restaurant-bogota/orders']=[{'id':id,'public_code':PAYLOAD,'status':'accepted','payment_status':PAYLOAD}]
    d={'id':id,'order_id':id,'status':'quoted','destination_address':PAYLOAD,'destination_city':PAYLOAD,
       'provider':PAYLOAD,'fee_minor':100,'courier_name':PAYLOAD,'provider_delivery_reference':PAYLOAD,
       'tracking_url':'javascript:window.auditXss=true'}
    overrides['/api/operator/restaurants/demo-restaurant-bogota/deliveries']=[d]
    page.goto('https://commerce.test/delivery')
    page.get_by_role('button',name='Despachar courier').wait_for()
    assert PAYLOAD in page.locator('#rows').inner_text()
    assert not page.get_by_role('link',name='Tracking provider').count()
    assert_safe(page,errors,external)
    # An ID remains captured data; no HTML/JS interpolation. API will reject fake ID.
    page.on('dialog',lambda dialog:dialog.dismiss())
    page.get_by_role('button',name='Despachar courier').click()
    assert any(method=='POST' and '/delivery/dispatch' in path for method,path,_ in requests)
    assert_safe(page,errors,external)
    d['tracking_url']='https://tracking.example.test/order/1'
    page.get_by_role('button',name='Actualizar',exact=True).click()
    page.get_by_role('link',name='Tracking provider').wait_for()
    assert page.get_by_role('link',name='Tracking provider').get_attribute('href')==d['tracking_url']


def test_growth_text_and_quoted_message_arguments(site):
    page, _, overrides, requests, errors, external=site
    base='/api/operator/restaurants/demo-restaurant-bogota/'
    overrides[base+'promotions']=[{'code':PAYLOAD,'name':PAYLOAD,'discount_type':'fixed','value':100,'minimum_order_minor':0}]
    overrides[base+'rewards']=[{'name':PAYLOAD,'description':PAYLOAD,'points_cost':10,'discount_minor':100}]
    overrides[base+'outbox']=[{'id':'message','status':'queued','message_kind':PAYLOAD,'body':PAYLOAD,'destination':'3005550101','scheduled_at':'2026-10-29T12:00:00Z','suppression_reason':PAYLOAD}]
    overrides['/api/operator/outbox/message/handoff']=overrides[base+'outbox'][0]
    page.goto('https://commerce.test/growth')
    page.get_by_role('button',name='Abrir WhatsApp').wait_for()
    for id in ['promos','rewards','outbox']: assert PAYLOAD in page.locator('#'+id).inner_text()
    assert_safe(page,errors,external)
    # Capture window.open without opening a real messaging provider.
    page.evaluate('window.open=(...args)=>{window.openArgs=args;return null}')
    page.on('dialog',lambda dialog:dialog.dismiss())
    page.get_by_role('button',name='Abrir WhatsApp').click()
    playwright.expect(page.get_by_role('button',name='Abrir WhatsApp')).to_be_enabled()
    assert page.evaluate('window.openArgs[0]').startswith('https://wa.me/3005550101?text=')
    assert page.evaluate('window.openArgs[2]')=='noopener,noreferrer'
    assert_safe(page,errors,external)


@pytest.mark.parametrize('value', ['javascript:alert(1)','data:text/html,<script>1</script>','//evil.test/a',
    'https://tracking.example.test.evil.test/a','https://user@tracking.example.test/a',
    'https://tracking.example.test\\@evil.test/a',' https://tracking.example.test/a','/admin','/demo/delivery/../admin'])
def test_url_policy_denies_unsafe_destinations(site,value):
    page,_,_,_,_,_=site
    page.goto('https://commerce.test/admin');playwright.expect(page.locator("#orders")).to_contain_text("Sin pedidos")
    assert page.evaluate('(value)=>CommerceUI.safeURL(value,"tracking")',value) is None


@pytest.mark.parametrize('width',[320,390,1440])
def test_layout_and_keyboard_smoke(site,width):
    page,_,_,_,errors,external=site
    page.set_viewport_size({'width':width,'height':900})
    for route in ['/','/admin','/delivery','/growth']:
        page.goto('https://commerce.test'+route)
        page.wait_for_load_state('networkidle')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement !== document.body')
        assert_safe(page,errors,external)
        artifact_dir=os.environ.get('COMMERCE_BROWSER_ARTIFACTS')
        if artifact_dir:
            from pathlib import Path
            folder=Path(artifact_dir);folder.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(folder / ((route.strip('/') or 'index')+'-'+str(width)+'.png')),full_page=True)


def test_customer_checkout_and_reservation_controls(site):
    page,client,_,requests,errors,external=site
    page.goto('https://commerce.test/')
    article=page.locator('#menu article').filter(has_text='Smash 101')
    article.get_by_role('button').click()
    page.locator('#modifierGroups input[type=radio]').first.check()
    page.get_by_role('button',name='Agregar al pedido',exact=True).click()
    page.locator('#cName').fill('Browser customer')
    page.locator('#cPhone').fill('3005550133')
    page.locator('#checkoutButton').click()
    playwright.expect(page.locator('#notice')).to_contain_text('Pago demo aprobado')
    assert sum(method=='POST' and path.endswith('/orders') for method,path,_ in requests)==1
    page.get_by_role('button',name='Reservar',exact=True).click()
    page.locator('#rName').fill('Browser reservation')
    page.locator('#rPhone').fill('3005550134')
    when=(datetime.now()+timedelta(days=2)).replace(hour=12,minute=0,second=0,microsecond=0)
    page.locator('#rDate').fill(when.strftime('%Y-%m-%dT%H:%M'))
    page.get_by_role('button',name='Solicitar reserva').click()
    playwright.expect(page.locator('#notice')).to_contain_text('solicitada')
    assert_safe(page,errors,external)


def test_checkout_redirect_policy_and_strict_csp(site):
    page,client,overrides,_,errors,external=site
    url='/api/restaurants/demo-restaurant-bogota/storefront'
    store=client.get(url).json(); store['payment_provider']='wompi'; overrides[url]=store
    overrides['/api/restaurants/demo-restaurant-bogota/orders']={
        'public_code':PAYLOAD,'payments':[{'checkout_url':'javascript:window.auditXss=true'}]}
    page.goto('https://commerce.test/')
    page.locator('#menu article').filter(has_text='Smash 101').get_by_role('button').click()
    page.locator('#modifierGroups input[type=radio]').first.check()
    page.get_by_role('button',name='Agregar al pedido',exact=True).click()
    page.locator('#cName').fill('Customer');page.locator('#cPhone').fill('3005550133')
    page.locator('#checkoutButton').click()
    playwright.expect(page.locator('#notice')).to_contain_text('Enlace de pago no autorizado')
    assert PAYLOAD in page.locator('#notice').inner_text()
    assert page.url=='https://commerce.test/'
    assert page.evaluate('CommerceUI.safeURL("https://checkout.example.test/pay/1","checkout")')=='https://checkout.example.test/pay/1'
    assert page.evaluate('CommerceUI.safeURL("https://tracking.example.test/pay/1","checkout")') is None
    assert_safe(page,errors,external)
    # Confirm enforcement, not just the presence of a CSP header.
    page.evaluate("""() => {const s=document.createElement('script');s.textContent='window.cspFailed=true';document.body.appendChild(s);}""")
    assert page.evaluate('window.cspFailed !== true')


def test_real_delivery_controls_and_growth_plan(site):
    page,client,_,requests,errors,external=site
    quote=client.post('/api/restaurants/demo-restaurant-bogota/delivery/quote',json={
        'destination':{'address_line':'Calle 85 # 12-34','city':'Bogotá','latitude':4.6697,'longitude':-74.0549}})
    assert quote.status_code==200,quote.text
    o=order(client,fulfillment_type='delivery',delivery_quote_id=quote.json()['id'])
    assert client.post(f'/api/payments/simulated/{o["payments"][0]["provider_reference"]}/complete').status_code==200
    headers=staff_headers(client)
    for status in ['accepted','preparing','ready']:
        assert client.patch('/api/operator/orders/'+o['id'],json={'status':status},headers=headers).status_code==200
    page.goto('https://commerce.test/delivery')
    page.get_by_role('button',name='Despachar courier').click()
    page.get_by_role('button',name='Recogido',exact=True).click()
    page.get_by_role('button',name='Entregado',exact=True).click()
    playwright.expect(page.locator('#rows .status')).to_have_text('delivered')
    assert_safe(page,errors,external)
    page.goto('https://commerce.test/growth')
    page.get_by_role('button',name='Planear win-back').click()
    playwright.expect(page.locator('#metrics')).to_contain_text('Pedidos completos')
    assert any(method=='POST' and path.endswith('/winback/plan') for method,path,_ in requests)
    assert_safe(page,errors,external)


def test_reservation_checkbox_records_only_explicit_request(site):
    from world_model.restaurant_commerce.models import Reservation, Customer
    from sqlalchemy import select
    import json
    page,client,_,requests,errors,external=site
    page.goto('https://commerce.test/')
    page.get_by_role('button',name='Reservar',exact=True).click()
    assert not page.locator('#rWhatsappOptIn').is_checked()
    for opted,phone in [(False,'3007770001'),(True,'3007770002')]:
        if opted:
            page.once('dialog', lambda dialog: dialog.accept())
            page.locator('#newReservation').click()
            assert not page.locator('#rWhatsappOptIn').is_checked()
        page.locator('#rName').fill('Consent fixture');page.locator('#rPhone').fill(phone)
        when=(datetime.now()+timedelta(days=2)).replace(hour=12,minute=0,second=0,microsecond=0)
        page.locator('#rDate').fill(when.strftime('%Y-%m-%dT%H:%M'))
        page.locator('#rWhatsappOptIn').set_checked(opted)
        with page.expect_response(lambda r:r.url.endswith('/reservations') and r.request.method=='POST') as response:
            page.get_by_role('button',name='Solicitar reserva').click()
        assert response.value.status==200
        body=response.value.json()
        with client.app.state.session_factory() as session:
            row=session.get(Reservation,body['id']);snap=json.loads(row.customer_snapshot_json)
            assert snap['whatsapp_requested'] is opted
            assert not session.get(Customer,row.customer_id).whatsapp_opt_in
    assert_safe(page,errors,external)


def test_real_composer_handoff_never_sends_and_checks_revocation(site):
    from world_model.restaurant_commerce.models import Customer, OutboundMessage
    page,client,_,requests,errors,external=site
    with client.app.state.session_factory() as session:
        customer=Customer(business_id='demo-restaurant-bogota',phone='3007770011',name='Consent fixture',whatsapp_opt_in=True,marketing_opt_in=True,whatsapp_verified_at=datetime.now(timezone.utc),marketing_verified_at=datetime.now(timezone.utc))
        session.add(customer);session.flush()
        message=OutboundMessage(business_id=customer.business_id,customer_id=customer.id,purpose='marketing',message_kind='winback',
            destination=customer.phone,body=PAYLOAD,scheduled_at=datetime.now(timezone.utc)-timedelta(minutes=1),dedupe_key='browser-handoff')
        session.add(message);session.commit();mid=message.id;cid=customer.id
    page.goto('https://commerce.test/growth')
    page.get_by_role('button',name='Abrir WhatsApp').wait_for()
    page.evaluate('window.open=(...args)=>{window.openArgs=args;return null}')
    page.get_by_role('button',name='Abrir WhatsApp').click()
    playwright.expect(page.locator('#outbox')).to_contain_text('handed_off')
    assert page.evaluate('window.openArgs[0]').startswith('https://wa.me/3007770011?text=')
    assert not any(path.endswith('/sent') for _,path,_ in requests)
    with client.app.state.session_factory() as session:
        row=session.get(OutboundMessage,mid);assert row.status=='handed_off' and row.sent_at is None
        session.get(Customer,cid).marketing_opt_in=False;session.commit()
    page.evaluate('window.openArgs=null')
    page.on('dialog',lambda dialog:dialog.dismiss())
    with page.expect_response(lambda r:r.url.endswith('/handoff')) as response:
        page.get_by_role('button',name='Abrir WhatsApp').click()
    assert response.value.status==422
    assert page.evaluate('window.openArgs===null')
    assert_safe(page,errors,external)
