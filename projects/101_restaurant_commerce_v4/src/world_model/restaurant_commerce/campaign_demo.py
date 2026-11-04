"""Isolated synthetic Honorato campaign pilot. No real customer/catalog/provider data."""
import argparse
import json
from datetime import datetime, timezone
from sqlalchemy import select
from .api import create_app
from .models import RestaurantCommerceProfile, Menu, MenuCategory, MenuItem, Customer
from .campaign_models import CampaignSettings
from .campaigns import set_permission, canonical
from .campaign_delivery import FakeTransport
from .staff import provision

BUSINESS = 'honorato-campaign-test'
OTHER = 'other-campaign-test'
CLOCK = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)
PASSWORD = 'synthetic campaign demonstration only'


def seed_campaign_demo(session):
    if session.get(CampaignSettings, BUSINESS): return
    for bid, name in ((BUSINESS,'Honorato · demostración'),(OTHER,'Otro negocio · demostración')):
        session.add(RestaurantCommerceProfile(business_id=bid,slug=bid,display_name=name))
        session.flush()
        menu = Menu(business_id=bid,name='Carta de prueba')
        session.add(menu); session.flush()
        category = MenuCategory(menu_id=menu.id,name='Solo demostración')
        session.add(category); session.flush()
        session.add(MenuItem(category_id=category.id,name='Producto de prueba',
            description='Artículo ficticio para verificar el checkout. No es un producto publicado de Honorato.',base_price_minor=24900,currency='COP'))
        session.add(CampaignSettings(business_id=bid,scope='test',config_json=canonical({
            'sender':'demostracion@example.test','brand':{'name':name,'tone':'Cálido, sencillo, humano',
                'examples':['Una invitación a volver a la mesa.'],'facts':[],
                'logo_path':'/assets/brand-ad5abbbd672d1f408b7eb235e06e3f435acad153d08bec2c316f5708037ec730.png' if bid==BUSINESS else None,
                'logo_sha256':'ad5abbbd672d1f408b7eb235e06e3f435acad153d08bec2c316f5708037ec730',
                'images':[],
                'provenance':'Retained website logo observation, 2026-10-27; local preview only. No verified offers or product facts used'},
            'simulation_clock':CLOCK.isoformat(),'frequency_hours':24,
            'holidays':{'2026':['2026-01-01','2026-01-12','2026-03-23','2026-04-02','2026-04-03',
                '2026-05-01','2026-05-18','2026-06-08','2026-06-15','2026-06-29','2026-07-20',
                '2026-08-07','2026-08-17','2026-10-12','2026-11-02','2026-11-16','2026-12-08','2026-12-25']},
            'holiday_source':'test fixture; requires current official review before activation'})))
        session.flush()
        for index,(label,state) in enumerate([('Ana ficticia','granted'),('Sin nombre','granted'),('Retiro ficticio','withdrawn'),
                    ('Queja ficticia','suppressed'),('Sin correo','granted'),('Sin evidencia','unknown'),('RNE vencido','granted')]):
            customer = Customer(business_id=bid,phone=f'+5730055501{index:02d}',name=None if index==1 else label,
                email=None if index==4 else f'persona{index}@example.test')
            session.add(customer); session.flush()
            if index != 5:
                set_permission(session,bid,customer.id,channel='email',scope='test',state=state,
                    source='synthetic-fixture:explicit-email-permission',reason='complaint' if index==3 else None,
                    registry={'state':'clear','scope':'test','source':'synthetic-rne-review',
                        'expires_at':'2026-11-01T00:00:00+00:00' if index==6 else '2026-11-10T00:00:00+00:00'},now=CLOCK)
        session.commit()
    provision(session,'campaign.manager',PASSWORD,BUSINESS,'manager',actor='synthetic-fixture')
    provision(session,'other.manager',PASSWORD,OTHER,'manager',actor='synthetic-fixture')


def app_for_demo(database_url, *, base_url='http://127.0.0.1:8799', recovery=False):
    adapter = FakeTransport()
    options = {'integrations':{'honorato-test':{'business_id':BUSINESS,'scope':'test','adapter':adapter},
                              'other-test':{'business_id':OTHER,'scope':'test','adapter':FakeTransport('other-test-secret')}},
               'clock':lambda:CLOCK,'base_url':base_url}
    app = create_app(database_url=database_url, demo_mode=True, environment='development',
        campaign_options=options,payment_recovery_enabled=recovery,
        webhook_secrets={'simulated':'synthetic-campaign-payment-secret'})
    with app.state.session_factory() as session: seed_campaign_demo(session)
    app.state.campaign_options = options
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='/tmp/101-campaign-demo.db')
    parser.add_argument('--port', type=int, default=8799)
    parser.add_argument('--worker', action='store_true', help='Run existing recovery worker automatically; otherwise use screen simulation button')
    parser.add_argument('--sms',action='store_true',help='Enable explicit synthetic SMS route fixture')
    parser.add_argument('--whatsapp',action='store_true',help='Enable explicit synthetic WhatsApp account/template fixture')
    args = parser.parse_args()
    import uvicorn
    app = app_for_demo('sqlite:///' + args.db, base_url=f'http://127.0.0.1:{args.port}', recovery=args.worker)
    if args.whatsapp:
        with app.state.session_factory() as session:
            app.state.campaign_options['integrations']['honorato-whatsapp-test']=enable_whatsapp_demo(session,origin=f'http://127.0.0.1:{args.port}')
    if args.sms:
        with app.state.session_factory() as session:
            app.state.campaign_options['integrations']['honorato-sms-test']=enable_sms_demo(session,origin=f'http://127.0.0.1:{args.port}')
    print(f'TEST ONLY: http://127.0.0.1:{args.port}/campaigns; user campaign.manager; password: {PASSWORD}')
    print('Fixed simulation clock:',CLOCK.isoformat(),'; contacts, catalog, permissions and RNE are synthetic.')
    uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False)





def enable_whatsapp_demo(session, *, origin='http://127.0.0.1:8801'):
    """Explicit synthetic account/template/permission fixture; no Meta approval claim."""
    from . import whatsapp as w
    from .campaign_models import WhatsAppSender, ContactPermission
    from .whatsapp_delivery import FakeWhatsAppTransport
    if not session.get(WhatsAppSender,BUSINESS):
        w.configure(session,BUSINESS,w.SenderInput(phone_id='10100000001',waba_id='10100000002',version='v23.0',
            display_phone='+573005550199',support_owner='campaign.manager',link_origin=origin,status='READY',quality='GREEN',
            allowance=10,source='synthetic fixture; not Meta verification',expires_at='2026-11-10T00:00:00Z',unit_cost_microusd=0),CLOCK)
        w.put_template(session,BUSINESS,w.TemplateInput(provider_id='10100000003',name='honorato_demo',language='es',
            category='MARKETING',status='APPROVED',body='Hola {{1}}. {{2}}',footer='Responde BAJA para retirar tu permiso.',
            source='synthetic template approval; not Meta approval',expires_at='2026-11-10T00:00:00Z'),CLOCK)
        for customer in session.scalars(select(Customer).where(Customer.business_id==BUSINESS)):
            permission=session.scalar(select(ContactPermission).where(ContactPermission.customer_id==customer.id,ContactPermission.channel=='email'))
            if permission:
                set_permission(session,BUSINESS,customer.id,channel='whatsapp',scope='test',state=permission.state,
                    source='synthetic explicit WhatsApp permission',reason=permission.reason,registry=json.loads(permission.registry_json),now=CLOCK)
        session.commit()
    return {'business_id':BUSINESS,'scope':'test','adapter':FakeWhatsAppTransport()}

def enable_sms_demo(session, *, origin='http://127.0.0.1:8802'):
    import regex  # campaign-sms extra; fail before starting an incomplete demo
    from twilio.request_validator import RequestValidator
    from . import sms
    from .campaign_models import SmsSender,ContactPermission
    from .sms_delivery import FakeSmsTransport
    if not session.get(SmsSender,BUSINESS):
        sms.configure(session,BUSINESS,sms.SenderInput(account_sid='AC'+'1'*32,sender='+15555550199',
            route='international_long_code',link_origin=origin,status='READY',inbound_supported=True,
            delivery_receipts='available',max_segments=10,unit_cost_microusd=0,
            source='synthetic route and price; not Twilio verification',expires_at='2026-11-10T00:00:00Z'),CLOCK)
        for customer in session.scalars(select(Customer).where(Customer.business_id==BUSINESS)):
            permission=session.scalar(select(ContactPermission).where(ContactPermission.customer_id==customer.id,ContactPermission.channel=='email'))
            if permission:
                set_permission(session,BUSINESS,customer.id,channel='sms',scope='test',state=permission.state,
                    source='synthetic explicit SMS permission',reason=permission.reason,registry=json.loads(permission.registry_json),now=CLOCK)
        session.commit()
    return {'business_id':BUSINESS,'scope':'test','adapter':FakeSmsTransport(origin=origin)}

if __name__ == '__main__': main()
