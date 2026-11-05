"""Real HTTP/Chromium owner lifecycle, without contacting a real provider."""
import json
import os
import socket
import threading
import time
from pathlib import Path
import pytest
import uvicorn
from cryptography.fernet import Fernet
from test_browser_security import browser, playwright
from world_model.restaurant_commerce.connections_demo import app_for_demo
from world_model.restaurant_commerce.campaign_demo import PASSWORD


@pytest.fixture
def live(tmp_path,browser):
    sock=socket.socket();sock.bind(('127.0.0.1',0));url='http://127.0.0.1:'+str(sock.getsockname()[1])
    app=app_for_demo('sqlite:///'+str(tmp_path/'connections.db'),Fernet.generate_key())
    server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    for _ in range(100):
        if server.started:break
        time.sleep(.05)
    assert server.started
    context=browser.new_context(base_url=url,viewport={'width':1440,'height':1000});page=context.new_page();errors=[];external=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:external.append(r.url) if not r.url.startswith(url) else None)
    try:yield page,context,url,errors,external
    finally:context.close();server.should_exit=True;thread.join(timeout=10);sock.close()


def test_connect_select_sync_disconnect_and_reconnect(live):
    page,context,url,errors,external=live
    out=Path(os.environ.get('CONNECTIONS_BROWSER_EVIDENCE','/tmp/101-connections-evidence/browser'));out.mkdir(parents=True,exist_ok=True)
    page.goto('/connections');page.locator('#staffUsername').fill('campaign.manager');page.locator('#staffPassword').fill(PASSWORD);page.locator('#staffSignIn').click()
    playwright.expect(page.locator('#state')).to_have_text('Sin conexión')
    playwright.expect(page.locator('#mode')).to_contain_text('DEMOSTRACIÓN')
    page.locator('#connect').click();playwright.expect(page.get_by_text('SIMULADOR LOCAL · NO ES GOOGLE')).to_be_visible()
    page.locator('#deny').click();playwright.expect(page.locator('#state')).to_have_text('Autorización cancelada')
    page.locator('#connect').click();page.locator('#allow').click()
    playwright.expect(page.locator('#locations option')).to_have_count(2,timeout=15000)
    page.locator('#select').click();playwright.expect(page.locator('#state')).to_have_text('Conectado',timeout=15000)
    playwright.expect(page.locator('#metrics tr')).to_have_count(3)
    playwright.expect(page.locator('#reviews')).to_contain_text('No describe una experiencia real')
    playwright.expect(page.locator('#locationTitle')).to_have_text('Honorato · ubicación ficticia')
    page.screenshot(path=str(out/'desktop.png'),full_page=True)
    page.reload();playwright.expect(page.locator('#metrics tr')).to_have_count(3)
    page.locator('#refresh').click();playwright.expect(page.locator('#notice')).to_contain_text('Espera un minuto')
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(out/'mobile.png'),full_page=True)
    page.on('dialog',lambda d:d.accept());page.locator('#disconnect').click();playwright.expect(page.locator('#state')).to_have_text('Sin conexión',timeout=15000)
    playwright.expect(page.locator('#dashboard')).to_be_hidden()
    page.locator('#connect').click();page.locator('#allow').click();playwright.expect(page.locator('#locations option')).to_have_count(2,timeout=15000)
    page.locator('#locations').select_option(index=1);page.locator('#select').click();playwright.expect(page.locator('#state')).to_have_text('Conectado',timeout=15000)
    playwright.expect(page.locator('#locationTitle')).to_have_text('Segunda ubicación ficticia')
    page.locator('#staffLogout').click();playwright.expect(page.locator('#content')).to_be_hidden()
    assert errors==[] and external==[]
    (out/'summary.json').write_text(json.dumps({'url':url,'journey':'deny,connect,select,sync,reload,disconnect,reconnect,logout','errors':errors,'external_requests':external},indent=2)+'\n')


def test_cross_site_google_return_preserves_strict_staff_cookie(live):
    from html import escape
    from urllib.parse import urlencode,parse_qs,urlsplit
    page,context,url,errors,external=live
    page.goto('/connections');page.locator('#staffUsername').fill('campaign.manager');page.locator('#staffPassword').fill(PASSWORD);page.locator('#staffSignIn').click()
    playwright.expect(page.locator('#state')).to_have_text('Sin conexión')
    me=context.request.get('/api/staff/me').json()
    root='/api/operator/restaurants/'+me['businesses'][0]['business_id']+'/connections/google/authorize'
    grant=context.request.post(root,headers={'X-101-CSRF':me['csrf']}).json()
    state=parse_qs(urlsplit(grant['url']).query)['state'][0]
    callback=url+'/connections/google/callback?'+urlencode({'state':state,'code':'synthetic-owner-grant'})
    # An intercepted cross-site page simulates Google's redirect without network.
    context.route('https://google.example.test/**',lambda route:route.fulfill(content_type='text/html',body='<a id="return" href="'+escape(callback)+'">Return</a>'))
    callbacks=[]
    page.on('request',lambda r:callbacks.append(r.all_headers()) if '/connections/google/callback?' in r.url else None)
    page.goto('https://google.example.test/consent');page.locator('#return').click()
    playwright.expect(page.locator('#locations option')).to_have_count(2,timeout=15000)
    assert callbacks and 'commerce_staff=' not in callbacks[0].get('cookie','')
    assert errors==[] and external==['https://google.example.test/consent']
