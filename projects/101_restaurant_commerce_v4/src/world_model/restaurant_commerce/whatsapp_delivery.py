"""Official WhatsApp Cloud API wire contract; simulator makes no network calls."""
import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from .campaign_delivery import FakeTransport, Submission


def error_reason(code):
    return {131048: 'whatsapp_quality_limit', 131049: 'whatsapp_recipient_marketing_limit',
            131050: 'whatsapp_opt_out', 132015: 'whatsapp_template_paused',
            132016: 'whatsapp_template_disabled', 132001: 'whatsapp_template_missing',
            132000: 'whatsapp_template_parameters', 130429: 'whatsapp_throughput_limit',
            131056: 'whatsapp_pair_limit', 80007: 'whatsapp_account_limit',
            190: 'whatsapp_credentials_invalid'}.get(code, 'whatsapp_provider_rejection')


class WhatsAppCloudTransport:
    name = 'whatsapp_cloud'
    capabilities = {'network': True, 'idempotency': False, 'delivery_receipts': True,
                    'read_events': True, 'inbound_replies': True}

    def __init__(self, *, phone_id, waba_id, version, token, app_secret, verify_token, client=None):
        import httpx
        self.phone_id, self.waba_id, self.version = phone_id, waba_id, version
        self.token, self.app_secret, self.verify_token = token, app_secret, verify_token
        self.client = client or httpx.Client(timeout=15, follow_redirects=False)

    @classmethod
    def from_environment(cls, *, phone_id, waba_id, version, secret_prefix):
        import os
        if not re.fullmatch(r'WHATSAPP_[A-Z0-9_]+', secret_prefix): raise ValueError('invalid_secret_reference')
        return cls(phone_id=phone_id, waba_id=waba_id, version=version,
            token=os.environ.get(secret_prefix+'_TOKEN', ''),
            app_secret=os.environ.get(secret_prefix+'_APP_SECRET', ''),
            verify_token=os.environ.get(secret_prefix+'_VERIFY_TOKEN', ''))

    def validate(self):
        reasons = []
        if not re.fullmatch(r'\d{5,30}', self.phone_id) or not re.fullmatch(r'\d{5,30}', self.waba_id): reasons.append('whatsapp_sender_invalid')
        if not re.fullmatch(r'v\d{2}\.0', self.version): reasons.append('whatsapp_version_required')
        if not all([self.token, self.app_secret, self.verify_token]): reasons.append('whatsapp_credentials_unconfigured')
        return reasons

    def submit(self, message):
        if self.validate() or message.sender != self.phone_id or not re.fullmatch(r'\+57\d{10}', message.destination):
            return Submission('rejected', reason='whatsapp_configuration_or_destination')
        payload = {'messaging_product': 'whatsapp', 'recipient_type': 'individual',
                   'to': message.destination[1:], 'biz_opaque_callback_data': message.key}
        if message.template: payload.update(type='template', template=message.template)
        else: payload.update(type='text', text={'body': message.text, 'preview_url': False})
        try:
            r = self.client.post(f'https://graph.facebook.com/{self.version}/{self.phone_id}/messages',
                headers={'Authorization': 'Bearer '+self.token}, json=payload)
            if r.status_code >= 500: return Submission('unknown', reason='whatsapp_outcome_unknown')
            data = r.json()
            if 200 <= r.status_code < 300:
                mid = data['messages'][0]['id']
                if not isinstance(mid, str) or not mid.startswith('wamid.'): raise ValueError('invalid_message_id')
                return Submission('accepted', mid)
            code = data.get('error', {}).get('code')
            if isinstance(code, int) and 400 <= r.status_code < 500:
                return Submission('rejected', reason=error_reason(code))
        except Exception:
            pass
        return Submission('unknown', reason='whatsapp_outcome_unknown')

    def readiness(self):
        """Explicit read-only probe, never called on UI load or by simulation."""
        if self.validate(): raise ValueError('whatsapp_configuration_incomplete')
        headers = {'Authorization': 'Bearer '+self.token}
        root = f'https://graph.facebook.com/{self.version}'
        phone = self.client.get(root+'/'+self.phone_id, headers=headers,
            params={'fields': 'id,verified_name,quality_rating,code_verification_status'})
        phone.raise_for_status()
        templates = self.client.get(root+'/'+self.waba_id+'/message_templates', headers=headers,
            params={'fields': 'id,name,language,status,category,components', 'limit': 100})
        templates.raise_for_status(); data = templates.json()
        return {'phone': phone.json(), 'templates': data['data'],
            'templates_complete': not bool(data.get('paging', {}).get('next')),
            'allowance': 'requires_current_account_review'}

    def account_readiness(self):
        observation=self.readiness()
        response=self.client.get(f'https://graph.facebook.com/{self.version}/{self.waba_id}/phone_numbers',
            headers={'Authorization':'Bearer '+self.token},params={'fields':'id','limit':100})
        response.raise_for_status();data=response.json()
        observation['phone_waba_binding_verified']=any(p.get('id')==self.phone_id for p in data['data'])
        observation['phone_catalogue_complete']=not bool(data.get('paging',{}).get('next'))
        return observation

    def challenge(self, mode, supplied, challenge):
        if mode != 'subscribe' or not self.verify_token or not hmac.compare_digest(supplied or '', self.verify_token):
            raise ValueError('invalid_verification_token')
        if not challenge or len(challenge) > 200: raise ValueError('invalid_challenge')
        return challenge

    def verify_events(self, body, signature):
        expected = 'sha256='+hmac.new(self.app_secret.encode(), body, hashlib.sha256).hexdigest()
        if not self.app_secret or not signature or not hmac.compare_digest(signature, expected): raise ValueError('invalid_signature')
        data = json.loads(body)
        if data.get('object') != 'whatsapp_business_account': raise ValueError('wrong_object')
        events = []
        for entry in data['entry']:
            if entry['id'] != self.waba_id: raise ValueError('wrong_waba')
            for change in entry['changes']:
                value = change['value']
                if change['field'] == 'message_template_status_update':
                    at = datetime.fromtimestamp(int(entry['time']), timezone.utc).isoformat()
                    events.append({'kind': 'template_status', 'template_id': str(value['message_template_id']),
                        'language': value['message_template_language'], 'status': value['event'], 'at': at,
                        'id': f"template:{value['message_template_id']}:{value['message_template_language']}:{value['event']}:{at}"})
                    continue
                if change['field'] != 'messages': raise ValueError('unsupported_field')
                if value.get('messaging_product') != 'whatsapp' or value['metadata']['phone_number_id'] != self.phone_id: raise ValueError('wrong_phone')
                for status in value.get('statuses', []):
                    kind = {'sent': 'accepted', 'delivered': 'delivered', 'read': 'read', 'failed': 'failed'}.get(status['status'])
                    if not kind: raise ValueError('unsupported_status')
                    at = datetime.fromtimestamp(int(status['timestamp']), timezone.utc).isoformat()
                    events.append({'kind': kind, 'id': status['id']+':'+kind+':'+at,
                        'message_id': status['id'], 'key': status.get('biz_opaque_callback_data'),
                        'destination': '+'+status['recipient_id'], 'at': at,
                        'errors': [e['code'] for e in status.get('errors', [])]})
                for message in value.get('messages', []):
                    if message['type'] not in {'text','button','interactive','image','audio','video','document','sticker','location','contacts'}: continue
                    at = datetime.fromtimestamp(int(message['timestamp']), timezone.utc).isoformat()
                    text = message.get('text', {}).get('body', '')
                    if message['type'] == 'button': text = message['button'].get('payload', message['button'].get('text', ''))
                    if message['type'] == 'interactive': text = message['interactive'].get('button_reply', {}).get('id', '')
                    events.append({'kind': 'inbound', 'id': message['id'], 'message_id': message['id'],
                        'destination': '+'+message['from'], 'at': at, 'text': text, 'message_type': message['type']})
        if len(events) > 100: raise ValueError('batch_too_large')
        return events


class FakeWhatsAppTransport(FakeTransport, WhatsAppCloudTransport):
    name = 'simulated_whatsapp'
    capabilities = {**WhatsAppCloudTransport.capabilities, 'network': False}

    def __init__(self, phone_id='10100000001', waba_id='10100000002'):
        FakeTransport.__init__(self, 'synthetic-whatsapp-app-secret')
        self.phone_id, self.waba_id = phone_id, waba_id
        self.app_secret, self.verify_token = self.secret, 'synthetic-whatsapp-verification'
        self.version = 'v23.0'

    def submit(self, message):
        self.messages.setdefault(message.key, message)
        return Submission('accepted', 'wamid.simulated.'+message.key)
