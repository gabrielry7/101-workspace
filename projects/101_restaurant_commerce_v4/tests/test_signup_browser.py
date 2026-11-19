"""Real HTTP browser paths, including owner QR download and customer method choice."""
import json
import os
import re
import socket
import threading
import time
from pathlib import Path
import pytest
import uvicorn
from test_browser_security import browser, playwright
from world_model.restaurant_commerce.signup_demo import app_for_demo
from world_model.restaurant_commerce.campaign_demo import BUSINESS,OTHER,PASSWORD


@pytest.fixture
def site(tmp_path,browser):
    sock=socket.socket();sock.bind(('127.0.0.1',0));url='http://127.0.0.1:'+str(sock.getsockname()[1])
    app=app_for_demo('sqlite:///'+str(tmp_path/'signup.db'),url)
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


def test_owner_qr_phone_email_and_persistent_membership(site):
    page,context,url,errors,external=site
    out=Path(os.environ.get('SIGNUP_BROWSER_EVIDENCE','/tmp/101-signup-browser'));out.mkdir(parents=True,exist_ok=True)
    page.goto('/customers/signup');page.get_by_label('Usuario',exact=True).fill('campaign.manager');page.get_by_label('Contraseña',exact=True).fill(PASSWORD);page.get_by_role('button',name='Entrar',exact=True).click()
    playwright.expect(page.get_by_alt_text(re.compile('^Código QR de registro'))).to_be_visible();page.wait_for_function("()=>{const q=document.querySelector('.qr-card img');return q?.complete&&q.naturalWidth>100}")
    page.screenshot(path=str(out/'owner-desktop.png'),full_page=True)
    with page.expect_download() as result:page.get_by_role('link',name='Descargar PNG',exact=True).click()
    result.value.save_as(out/'signup-qr.png')
    website=page.get_by_label('Enlace de registro',exact=True).input_value();assert '?source=website' in website
    page.goto('/join/'+BUSINESS+'?source=qr')
    playwright.expect(page.locator('#phone')).to_be_visible()
    page.locator('#chooseEmail').click();playwright.expect(page.locator('#phoneFields')).to_be_hidden()
    page.locator('#email').fill('customer@example.test');page.locator('#sendCode').click()
    playwright.expect(page.locator('#demoCode')).to_contain_text('Código de prueba')
    code=re.search(r'\b\d{6}\b',page.locator('#demoCode').inner_text()).group()
    page.screenshot(path=str(out/'email-code.png'),full_page=True)
    page.locator('#code').fill(code);page.locator('#verifyCode').click()
    playwright.expect(page.locator('#welcome')).to_have_text('Ya eres parte.');playwright.expect(page.locator('#welcome')).to_be_visible()
    page.reload();playwright.expect(page.locator('#accountDetail')).to_contain_text('customer@example.test')
    page.locator('#visit').click()
    playwright.expect(page.locator('#customerSignup')).to_be_visible()
    assert page.locator('#customerSignup').get_attribute('href')=='/join/'+BUSINESS+'?source=website'
    page.goto('/join/'+OTHER);playwright.expect(page.locator('#join')).to_be_visible();page.locator('#join').click()
    playwright.expect(page.locator('#welcome')).to_have_text('Ya eres parte.');playwright.expect(page.locator('#welcome')).to_be_visible()
    page.locator('#logout').click();playwright.expect(page.locator('#phone')).to_be_visible()
    page.locator('#phone').fill('3005550100');page.locator('#sendCode').click()
    playwright.expect(page.locator('#demoCode')).to_contain_text('Código de prueba')
    code=re.search(r'\b\d{6}\b',page.locator('#demoCode').inner_text()).group()
    page.locator('#code').fill(code);page.locator('#verifyCode').click();playwright.expect(page.locator('#welcome')).to_have_text('Ya eres parte.');playwright.expect(page.locator('#welcome')).to_be_visible()
    page.screenshot(path=str(out/'phone-success.png'),full_page=True)
    page.locator('#logout').click();playwright.expect(page.locator('#phone')).to_be_visible()
    for width in [390,1440]:
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out/f'choice-{width}.png'),full_page=True)
    assert errors==[] and external==[]
    (out/'summary.json').write_text(json.dumps({'url':url,'phone_signup':True,'email_without_phone':True,'return_session':True,'second_business_membership':True,'qr_download':True,'errors':errors,'external_requests':external,'real_messages':0},indent=2)+'\n')
