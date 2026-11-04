#!/usr/bin/env python3
"""Complete a synthetic campaign over real local HTTP; never contact a provider."""
import argparse
import hashlib
import hmac
import json
import secrets
from pathlib import Path
from urllib.parse import urlsplit
import httpx


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8799')
    parser.add_argument('--channel',choices=['email','whatsapp'],default='email')
    parser.add_argument('--output',default='/tmp/101-campaign-rehearsal.json')
    args=parser.parse_args()
    parsed=urlsplit(args.url)
    if parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','localhost','::1'} or parsed.username or parsed.password:
        parser.error('Only a local synthetic campaign demo is supported')
    business='honorato-campaign-test'
    root='/api/operator/restaurants/'+business+'/campaigns'
    with httpx.Client(base_url=args.url,timeout=20,follow_redirects=False,trust_env=False) as client:
        def request(method,path,**kw):
            r=client.request(method,path,**kw);r.raise_for_status();return r
        assert request('GET','/api/browser-policy').json()['demo_mode'] is True
        request('POST','/api/staff/login',headers={'X-101-Login':'1'},json={
            'username':'campaign.manager','password':'synthetic campaign demonstration only'})
        headers={'X-101-CSRF':request('GET','/api/staff/me').json()['csrf']}
        data=request('GET',root).json();assert data['scope']=='test' and data['live_send_enabled'] is False
        draft={'sender':data['sender'],'content':{'subject':'Una invitación de Honorato · demo',
            'title':'La mesa está puesta.','body':'Una invitación de prueba para verificar el recorrido completo.',
            'terms':'Demostración sin oferta real. Catálogo, permisos y pago ficticios.'},
            'customer_ids':[x['id'] for x in data['customers']], 'scheduled_at':data['clock'],
            'expires_at':'2026-11-10T23:00:00+00:00','scope':'test','budget_microusd':0}
        wa_root='/api/operator/restaurants/'+business+'/whatsapp'
        if args.channel=='whatsapp':
            configuration=request('GET',wa_root).json()
            template=next(t for t in configuration['templates'] if t['name']=='honorato_demo')
            draft.update(channel='whatsapp',sender='10100000001',whatsapp_template_id=template['id'],
                whatsapp_parameters=['{name}','Invitación ficticia, solo demostración.'])
        campaign=request('POST',root,json=draft,headers=headers).json()
        if campaign['eligible']!=(3 if args.channel=='whatsapp' else 2):raise RuntimeError('Use a fresh demo database with the requested channel enabled')
        path=root+'/'+campaign['id']
        for action in ('approve','schedule'):
            request('POST',path+'/'+action,json={'digest':campaign['digest']},headers=headers)
        before=request('GET',path+'/report').json()
        withdrawal=next(x for x in data['customers'] if x['email']=='persona1@example.test')
        pending=next(j for j in before['deliveries'] if j['customer_id']==withdrawal['id'])
        if args.channel=='whatsapp':
            for message in ('Hola','BAJA'):
                request('POST',wa_root+'/simulate-inbound',json={'customer_id':withdrawal['id'],
                    'text':message,'request_key':secrets.token_hex(16)},headers=headers)
                if message=='Hola':
                    conversation=request('GET',wa_root+'/conversations').json()['conversations'][0]
                    request('POST',wa_root+'/conversations/'+conversation['id']+'/reply',
                        json={'body':'El equipo te ayuda con esta prueba.','request_key':secrets.token_hex(16)},headers=headers)
        else:
            request('POST',pending['unsubscribe_url'])
        request('POST',root+'/simulate/dispatch',headers=headers)
        deliveries=request('GET',path+'/report').json()
        assert next(j for j in deliveries['deliveries'] if j['id']==pending['id'])['state']=='skipped'
        job=next(j for j in deliveries['deliveries'] if j['state']=='accepted')
        if args.channel=='whatsapp':
            from datetime import datetime
            recipient=next(x for x in data['customers'] if x['id']==job['customer_id'])
            for kind in ('read','delivered','read'):
                event=json.dumps({'object':'whatsapp_business_account','entry':[{'id':'10100000002',
                    'changes':[{'field':'messages','value':{'messaging_product':'whatsapp',
                    'metadata':{'phone_number_id':'10100000001'},'statuses':[{'id':job['message_id'],
                    'recipient_id':recipient['phone'].lstrip('+'),'status':kind,
                    'timestamp':str(int(datetime.fromisoformat(data['clock']).timestamp())),
                    'biz_opaque_callback_data':job['id']}]}}]}]}).encode()
                signature='sha256='+hmac.new(b'synthetic-whatsapp-app-secret',event,hashlib.sha256).hexdigest()
                request('POST','/api/whatsapp-hooks/honorato-whatsapp-test',content=event,
                    headers={'X-Hub-Signature-256':signature})
            assert request('GET',wa_root+'/conversations').json()['conversations'][0]['replies'][0]['state']=='skipped'
        else:
            event=json.dumps({'id':'rehearsal-delivery','key':job['id'],'message_id':job['message_id'],
                'kind':'delivered','at':data['clock']},sort_keys=True).encode()
            signature=hmac.new(b'test-only-callback-secret',event,hashlib.sha256).hexdigest()
            for _ in range(2):request('POST','/api/campaign-hooks/honorato-test',content=event,headers={'X-Campaign-Signature':signature})
        assert client.get(root.replace(business,'other-campaign-test')).status_code==403
        assert client.get(job['tracking_url']+'tampered').status_code==404
        assert client.get(job['tracking_url']).status_code==303
        store=request('GET','/api/restaurants/'+business+'/storefront').json()
        item=store['menus'][0]['categories'][0]['items'][0]
        order=request('POST','/api/restaurants/'+business+'/orders',json={
            'customer':{'name':'Rehearsal customer','phone':'3005550100'},
            'items':[{'menu_item_id':item['id'],'quantity':1}],'payment_provider':'simulated',
            'idempotency_key':'campaign-rehearsal-'+secrets.token_hex(8),'recovery_secret':secrets.token_hex(32)}).json()
        assert request('GET',path+'/report').json()['paid_orders']==0
        reference=order['payments'][0]['provider_reference']
        request('POST','/api/payments/simulated/'+reference+'/complete',headers={'X-101-Order-Token':order['access_token']})
        refund=json.dumps({'event_id':'rehearsal-refund','provider_reference':reference,'status':'partially_refunded',
            'amount_minor':24900,'currency':'COP','refund_reference':'rehearsal-refund','refund_amount_minor':5000}).encode()
        signature=hmac.new(b'synthetic-campaign-payment-secret',refund,hashlib.sha256).hexdigest()
        for _ in range(2):request('POST','/api/webhooks/payments/simulated',content=refund,
            headers={'X-101-Webhook-Signature':signature})
        report=request('GET',path+'/report').json()
        assert (report['paid_orders'],report['captured_revenue'],report['refunds'],report['net_revenue'])==(1,24900,5000,19900)
        assert request('GET',path+'/report?scope=live').json()['paid_orders']==0
        evidence={k:v for k,v in report.items() if k not in {'deliveries','orders'}}
        evidence.update(channel=args.channel,campaign_id=campaign['id'],revision_sha256=campaign['digest'],
            unsubscribe_blocked=True,cross_business_status=403,duplicate_delivery_and_refund_stable=True,
            real_provider_calls=0,screen=args.url+'/campaigns')
        Path(args.output).write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps(evidence,indent=2))


if __name__=='__main__':main()
