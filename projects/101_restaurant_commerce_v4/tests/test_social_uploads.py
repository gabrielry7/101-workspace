import base64,hashlib,io
from datetime import datetime,timedelta,timezone
from PIL import Image
from test_social_production import social,env,factory,ROOT,OTHER,BUSINESS

def start(e,raw):
    return e.client.post(ROOT+'/uploads',headers=e.headers,json={'total':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'rights_statement':'Synthetic test material authorized for this fixture','expires_at':(datetime.now(timezone.utc)+timedelta(days=2)).isoformat(),'permitted_use':'production','fixture':True})

def test_large_resumable_photo_and_repeated_completion(social):
    out=io.BytesIO();Image.effect_noise((1200,1500),30).convert('RGB').save(out,format='PNG');raw=out.getvalue()
    assert len(raw)>500000
    r=start(social,raw);assert r.status_code==200,r.text
    route=ROOT+'/uploads/'+r.json()['id']
    first={'offset':0,'data_base64':base64.b64encode(raw[:262144]).decode()}
    for _ in range(2):assert social.client.put(route,headers=social.headers,json=first).json()['received']==262144
    assert social.client.get(route).json()['received']==262144
    assert social.client.post(route+'/complete',headers=social.headers).status_code==409
    assert social.client.get(route.replace(BUSINESS,OTHER)).status_code==403
    for offset in range(262144,len(raw),262144):
        r=social.client.put(route,headers=social.headers,json={'offset':offset,'data_base64':base64.b64encode(raw[offset:offset+262144]).decode()})
        assert r.status_code==200,r.text
    result=social.client.post(route+'/complete',headers=social.headers)
    assert result.status_code==200,result.text
    repeated=social.client.post(route+'/complete',headers=social.headers)
    assert repeated.json()['id']==result.json()['id']
    assert any(a['id']==result.json()['id'] for a in social.client.get(ROOT+'/assets').json()['assets'])

def test_upload_size_offsets_hash_and_cancel(social):
    raw=b'not an image';r=start(social,raw);route=ROOT+'/uploads/'+r.json()['id']
    assert social.client.put(route,json={'offset':0,'data_base64':base64.b64encode(raw).decode()}).status_code==403
    assert social.client.put(route,headers=social.headers,json={'offset':2,'data_base64':base64.b64encode(raw[:2]).decode()}).status_code==409
    assert social.client.put(route,headers=social.headers,json={'offset':0,'data_base64':base64.b64encode(raw).decode()}).status_code==200
    assert social.client.post(route+'/complete',headers=social.headers).status_code==422
    assert social.client.delete(route,headers=social.headers).status_code==200
    assert social.client.get(route).status_code==404
