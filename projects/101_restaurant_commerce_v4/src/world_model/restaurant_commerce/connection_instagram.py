"""Read-only Instagram Login adapter. Actual field access is established by probes.

No publishing, messaging, scraping, media download or paid API. Short-lived grants
are intentionally used until long-lived-token handling has separate qualification.
"""
import json
import os
import re
from datetime import timedelta, datetime, timezone
from urllib.parse import urlencode, urlsplit
import httpx
from .connection_google import ConnectionFailure
from .staff import aware

PROVIDER='instagram'
REQUIRED=('COMMERCE_INSTAGRAM_CLIENT_ID','COMMERCE_INSTAGRAM_CLIENT_SECRET',
          'COMMERCE_INSTAGRAM_REDIRECT_URI','COMMERCE_INSTAGRAM_API_VERSION','COMMERCE_INSTAGRAM_CONNECTION_KEY')
FIELDS='id,caption,media_type,permalink,timestamp'


def configuration():
    missing=[key for key in REQUIRED if not os.getenv(key)]
    return {'configured':not missing and os.getenv('COMMERCE_INSTAGRAM_CONNECTION_ENABLED')=='1',
            'missing':missing, 'enabled':os.getenv('COMMERCE_INSTAGRAM_CONNECTION_ENABLED')=='1'}


def from_environment():
    if not configuration()['enabled']:
        return None
    if configuration()['missing']:
        raise RuntimeError('Instagram configuration incomplete: '+', '.join(configuration()['missing']))
    from .connections import ConnectionRuntime
    uri=os.environ[REQUIRED[2]]
    parsed=urlsplit(uri)
    if (parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or
        parsed.path!='/connections/instagram/callback' or parsed.query or parsed.fragment):
        raise RuntimeError('Instagram requires an exact HTTPS /connections/instagram/callback URI')
    return ConnectionRuntime(InstagramAdapter(*(os.environ[k] for k in REQUIRED[:4])),os.environ[REQUIRED[4]])


def native_id(value):
    value=str(value or '')
    if not re.fullmatch(r'[0-9]{1,40}',value):
        raise ConnectionFailure('invalid_provider_resource')
    return value


class InstagramAdapter:
    provider=PROVIDER
    mode='live'
    automatic_sync=False
    local_disconnect_only=True
    capabilities={'read_profile':'probe_required','read_posts':'probe_required',
                  'post_counts':'probe_required','insights':'not_enabled', 'publish':False,'messages':False}

    def __init__(self,client_id,client_secret,redirect_uri,version,*,transport=None):
        if not re.fullmatch(r'v[0-9]{1,2}\.0',version):
            raise ValueError('Explicit supported Graph API version required')
        self.client_id,self.client_secret,self.redirect_uri,self.version=client_id,client_secret,redirect_uri,version
        self.transport=transport

    def authorize_url(self,state,verifier):
        # Do not claim PKCE support: authorization is bound to the existing staff
        # session, one-use state and server-side client-secret exchange.
        return 'https://www.instagram.com/oauth/authorize?'+urlencode({
            'client_id':self.client_id,'redirect_uri':self.redirect_uri,'response_type':'code',
            'scope':'instagram_business_basic','state':state})

    def request(self,method,path,*,token=None,params=None,data=None,exchange=False):
        origin='https://api.instagram.com' if exchange else 'https://graph.instagram.com'
        url=origin+path
        try:
            with httpx.Client(transport=self.transport,timeout=12,follow_redirects=False,trust_env=False) as client:
                with client.stream(method,url,params=params,data=data,
                        headers={'Authorization':'Bearer '+token} if token else {}) as response:
                    raw=bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw)>2_000_000:raise ConnectionFailure('provider_response_limit')
                    try: result=json.loads(raw)
                    except (ValueError,UnicodeError):raise ConnectionFailure('invalid_provider_response') from None
                    if not isinstance(result,dict):raise ConnectionFailure('invalid_provider_response')
                    if response.status_code>=400 or 'error' in result:
                        code=(result.get('error') or {}).get('code') if isinstance(result.get('error'),dict) else None
                        if response.status_code==401 or code==190:raise ConnectionFailure('reconnect_required')
                        if response.status_code==429:raise ConnectionFailure('rate_limited',retry=True)
                        if response.status_code>=500:raise ConnectionFailure('provider_unavailable',retry=True)
                        raise ConnectionFailure('permission_or_field_unavailable')
                    if response.status_code!=200:raise ConnectionFailure('invalid_provider_response')
                    return result
        except httpx.HTTPError:
            raise ConnectionFailure('provider_unavailable',retry=True) from None

    def exchange(self,code,verifier,now):
        result=self.request('POST','/oauth/access_token',exchange=True,data={
            'client_id':self.client_id,'client_secret':self.client_secret,'grant_type':'authorization_code',
            'redirect_uri':self.redirect_uri,'code':code})
        if 'data' in result:
            if 'access_token' in result or not isinstance(result['data'],list) or len(result['data'])!=1:
                raise ConnectionFailure('ambiguous_authorization')
            result=result['data'][0]
        if not isinstance(result,dict) or not isinstance(result.get('access_token'),str) or not result['access_token']:
            raise ConnectionFailure('invalid_provider_response')
        return {'access_token':result['access_token'],'user_id':native_id(result.get('user_id')),
                'expires_at':(now+timedelta(seconds=min(int(result.get('expires_in',3600)),3600))).isoformat(),
                'permissions':result.get('permissions'),'route':'instagram_login'}

    def refresh(self,tokens,now):
        # Never pretend an expired token refreshed successfully.
        if aware(datetime.fromisoformat(tokens['expires_at']))<=now+timedelta(seconds=30):
            raise ConnectionFailure('reconnect_required')
        return tokens

    def discover(self,tokens):
        user=native_id(tokens['user_id'])
        data=self.request('GET',f'/{self.version}/{user}',token=tokens['access_token'],params={'fields':'user_id,username'})
        actual=native_id(data.get('user_id') or data.get('id'))
        if actual!=user:raise ConnectionFailure('account_identity_mismatch')
        return [{'key':user,'name':str(data.get('username') or user),'provider':PROVIDER}]

    def snapshot(self,tokens,selected,now):
        user=native_id(selected)
        if user!=tokens['user_id']:raise ConnectionFailure('account_identity_mismatch')
        posts={};after=None;errors={};requests=0;has_more=False
        # At most2 pages of20 plus5 metric probes. Never follow arbitrary next URLs.
        for page in range(2):
            params={'fields':FIELDS,'limit':20}
            if after:params['after']=after
            data=self.request('GET',f'/{self.version}/{user}/media',token=tokens['access_token'],params=params)
            requests+=1
            if not isinstance(data.get('data'),list):raise ConnectionFailure('invalid_provider_response')
            for item in data['data'][:20]:
                pid=native_id(item.get('id'))
                timestamp=item.get('timestamp');normalized=None;offset=None;precision='unknown'
                if isinstance(timestamp,str):
                    try:
                        dt=datetime.fromisoformat(timestamp.replace('Z','+00:00'))
                        if dt.tzinfo:
                            normalized=dt.astimezone(timezone.utc).isoformat()
                            offset=dt.strftime('%z')
                            precision='second' if re.search(r'T[0-9]{2}:[0-9]{2}:[0-9]{2}',timestamp) else 'minute'
                        elif re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',timestamp):precision='day'
                    except ValueError:pass
                posts[pid]={'id':pid,'caption':str(item.get('caption',''))[:10000],
                    'format':str(item.get('media_type','unknown')),'published_at_native':timestamp,
                    'published_at_utc':normalized,'timestamp_precision':precision,'original_offset':offset,'business_timezone':None,
                    'observed_at':now.isoformat(),'capture_time':None,'distribution':'unknown',
                    'metrics':{'likes':{'value':None,'reason':'outside_probe_limit'},'comments':{'value':None,'reason':'outside_probe_limit'}},
                    'insights':{'value':None,'reason':'not_enabled'}}
            paging=data.get('paging') or {};after=(paging.get('cursors') or {}).get('after')
            has_more=bool(paging.get('next'))
            if not has_more:break
            if not isinstance(after,str) or len(after)>2048:raise ConnectionFailure('invalid_pagination')
        for pid,item in list(posts.items())[:5]:
            requests+=1
            try:
                counts=self.request('GET',f'/{self.version}/{pid}',token=tokens['access_token'],params={'fields':'like_count,comments_count'})
                for key,field in [('likes','like_count'),('comments','comments_count')]:
                    value=counts.get(field)
                    valid=type(value) is int and value>=0
                    item['metrics'][key]={'value':value if valid else None,'reason':None if valid else 'not_returned',
                        'definition':field,'period':'lifetime_at_observation','observed_at':now.isoformat()}
            except ConnectionFailure as exc:
                if exc.reason=='reconnect_required':raise
                errors[pid]=exc.reason
                for metric in item['metrics'].values():metric['reason']=exc.reason
        formats={}
        for item in posts.values():formats[item['format']]=formats.get(item['format'],0)+1
        return {'provider':PROVIDER,'api_version':self.version,'account_id':user,'observed_at':now.isoformat(),
                'posts':list(posts.values()),'errors':errors,'coverage':{'posts':len(posts),'requests':requests,
                'maximum_requests':7,'has_more':has_more,'history':'bounded_current_window'},
                'baseline':{'formats':formats,'reach':None,'orders':None,'reason':'not_available',
                            'interpretation':'descriptive_only_no_causal_or_timing_recommendation'}}

    def revoke(self,tokens):
        # Adapter does not claim remote revocation without a verified endpoint.
        raise ConnectionFailure('revoke_in_instagram_settings')
