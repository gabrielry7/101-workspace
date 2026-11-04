"""Twilio delivery-only adapter. No automatic retry or provider-side idempotency claim."""
import hashlib
import re
from urllib.parse import parse_qsl, urlsplit
from starlette.datastructures import FormData
from .campaign_delivery import FakeTransport, Submission

GSM_BASIC = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
GSM_EXTENDED = set('^{}\\[~]|€\f')


def segments(text):
    if not text or any(ord(c)<32 and c not in '\n\r\f' for c in text): raise ValueError('sms_invalid_text')
    import regex
    # Follow the provider calculator's indivisible encoded-grapheme boundaries.
    # CR/LF are separate GSM characters, not a combined Unicode grapheme.
    graphemes=[part for g in regex.findall(r'\X',text) for part in (list(g) if g=='\r\n' else [g])]
    gsm=all(len(g)==1 and (g in GSM_BASIC or g in GSM_EXTENDED) for g in graphemes)
    sizes=[(2 if g in GSM_EXTENDED else 1) if gsm else len(g.encode('utf-16-le'))//2 for g in graphemes]
    units=sum(sizes);single,multi,maximum=(160,153,1600) if gsm else (70,67,700)
    count=1
    if units>single:
        used=0
        for size in sizes:
            if used+size>multi:count+=1;used=0
            used+=size
    return {'encoding':'GSM-7' if gsm else 'UCS-2','units':units,'segments':count,
        'over_limit':units>maximum or (units>single and any(n>multi for n in sizes)),
        'rule':'twilio-co-grapheme-gsm160-153-ucs70-67-v2'}


def provider_reason(code):
    return {21610:'sms_opt_out',21614:'sms_non_mobile',21211:'sms_invalid_destination',
        21608:'sms_trial_recipient_unverified',21606:'sms_sender_unavailable',21408:'sms_country_permission',
        30007:'sms_carrier_filtered',30008:'sms_unknown_carrier_error',30034:'sms_registration_required',
        20003:'sms_credentials_invalid',20429:'sms_rate_limit'}.get(code,'sms_provider_rejection')


class TwilioTransport:
    name='twilio_sms'
    capabilities={'network':True,'idempotency':False,'delivery_receipts':True,'read_events':False,'inbound_replies':'route_specific'}

    def __init__(self, *, account_sid, auth_token, sender, callback_url, inbound_url, client=None):
        import httpx
        self.account_sid,self.auth_token,self.sender=account_sid,auth_token,sender
        self.callback_url,self.inbound_url=callback_url,inbound_url
        self.client=client or httpx.Client(timeout=15,follow_redirects=False,trust_env=False)

    @classmethod
    def from_environment(cls, *, secret_prefix, **config):
        import os
        if not re.fullmatch(r'TWILIO_[A-Z0-9_]+',secret_prefix): raise ValueError('invalid_secret_reference')
        return cls(auth_token=os.environ.get(secret_prefix+'_AUTH_TOKEN',''),**config)

    def validate(self):
        result=[]
        if not re.fullmatch(r'AC[a-fA-F0-9]{32}',self.account_sid) or not self.auth_token: result.append('twilio_credentials_unconfigured')
        if not re.fullmatch(r'(?:\+[1-9]\d{7,14}|\d{3,6})',self.sender):result.append('sms_sender_invalid')
        for value in [self.callback_url,self.inbound_url]:
            p=urlsplit(value)
            if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment:result.append('sms_callback_configuration')
        try:
            from twilio.request_validator import RequestValidator
            import regex
        except ImportError:result.append('twilio_validator_unavailable')
        return result

    def submit(self,message):
        if self.validate() or message.sender!=self.sender or not re.fullmatch(r'\+573\d{9}',message.destination):
            return Submission('rejected',reason='sms_configuration_or_destination')
        try:
            if segments(message.text)['over_limit']:return Submission('rejected',reason='sms_content_too_long')
            if not re.fullmatch(r'[a-f0-9]{64}',message.key):return Submission('rejected',reason='sms_delivery_key_invalid')
            r=self.client.post(f'https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json',
                auth=(self.account_sid,self.auth_token),data={'From':self.sender,'To':message.destination,
                'Body':message.text,'StatusCallback':self.callback_url+'?key='+message.key})
            if r.status_code>=500:return Submission('unknown',reason='sms_submission_unknown')
            data=r.json()
            if r.status_code==201 and re.fullmatch(r'SM[a-fA-F0-9]{32}',data.get('sid','')):
                if data.get('account_sid')!=self.account_sid or data.get('to')!=message.destination or data.get('from')!=self.sender:
                    return Submission('unknown',reason='sms_response_binding_mismatch')
                return Submission('accepted',data['sid'])
            if 400<=r.status_code<500 and isinstance(data.get('code'),int):
                # Terminal even for throttling; never retry to defeat recipient/route limits.
                return Submission('rejected',reason=provider_reason(data['code']))
        except Exception:pass
        return Submission('unknown',reason='sms_submission_unknown')

    def verify_callback(self,body,signature,*,key=None,inbound=False):
        from twilio.request_validator import RequestValidator
        if len(body)>16384 or not self.auth_token:raise ValueError('invalid_sms_callback')
        if not inbound and not re.fullmatch(r'[a-f0-9]{64}',key or ''):raise ValueError('invalid_delivery_key')
        form=FormData(parse_qsl(body.decode('utf-8'),keep_blank_values=True,strict_parsing=True,max_num_fields=80))
        url=self.inbound_url if inbound else self.callback_url+'?key='+key
        if not signature or not RequestValidator(self.auth_token).validate(url,form,signature):raise ValueError('invalid_signature')
        # Validate required single-valued fields after verifying every provider field.
        for name in ['AccountSid','MessageSid','From','To']+(['Body'] if inbound else ['MessageStatus']):
            if len(form.getlist(name))!=1:raise ValueError('ambiguous_sms_field')
        if form['AccountSid']!=self.account_sid or not re.fullmatch(r'SM[a-fA-F0-9]{32}',form['MessageSid']):raise ValueError('wrong_account_or_message')
        if any('\x00' in v for _,v in form.multi_items()) or (form['To'] if inbound else form['From'])!=self.sender:raise ValueError('wrong_sender')
        if not re.fullmatch(r'\+573\d{9}',form['From'] if inbound else form['To']):raise ValueError('invalid_country_or_destination')
        status='received' if inbound else form['MessageStatus']
        kinds={'accepted':'accepted','queued':'accepted','sending':'accepted','sent':'accepted',
            'delivered':'delivered','undelivered':'failed','failed':'failed','canceled':'rejected','received':'inbound'}
        if status not in kinds or (not inbound and status=='received'):raise ValueError('unsupported_sms_status')
        error=form.get('ErrorCode','')
        if len(form.getlist('ErrorCode'))>1 or (error and not re.fullmatch(r'\d{1,8}',error)):raise ValueError('invalid_error')
        text=form.get('Body','') if inbound else ''
        if len(text)>1600:raise ValueError('sms_body_too_long')
        result={'message_id':form['MessageSid'],'key':key,'kind':kinds[status],'provider_status':status,
            'destination':form['From'] if inbound else form['To'],'error':int(error) if error else None,'text':text,
            'provider_timestamp':None}
        result['id']=hashlib.sha256((form['MessageSid']+':'+status+':'+error).encode()).hexdigest()
        return result


class FakeSmsTransport(FakeTransport,TwilioTransport):
    name='simulated_sms'
    capabilities={**TwilioTransport.capabilities,'network':False}

    def __init__(self, *, origin='http://127.0.0.1:8802'):
        FakeTransport.__init__(self,'synthetic-sms-callback-secret')
        self.account_sid='AC'+'1'*32;self.auth_token=self.secret;self.sender='+15555550199'
        self.callback_url=origin+'/api/sms-hooks/honorato-sms-test/status'
        self.inbound_url=origin+'/api/sms-hooks/honorato-sms-test/incoming'

    def submit(self,message):
        self.messages.setdefault(message.key,message)
        return Submission('accepted','SM'+hashlib.sha256(message.key.encode()).hexdigest()[:32])
