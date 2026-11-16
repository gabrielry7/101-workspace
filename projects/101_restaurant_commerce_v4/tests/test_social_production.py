# ruff: noqa: F401,F811 -- imported pytest fixtures
import base64
import io
import json
import zipfile
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import pytest
from PIL import Image
from test_campaigns import env, factory, BUSINESS, OTHER
from world_model.restaurant_commerce.social_production import upgrade

ROOT='/api/operator/restaurants/'+BUSINESS+'/social'

@pytest.fixture
def social(env):
    with env.factory() as session:
        upgrade(session.get_bind())
    return env

def photo(env, **changes):
    out=io.BytesIO()
    Image.new('RGB',(1200,1500),'#986345').save(out,format='JPEG')
    data={'data_base64':base64.b64encode(out.getvalue()).decode(),'rights_statement':'Synthetic test image created for this test',
          'expires_at':(datetime.now(timezone.utc)+timedelta(days=2)).isoformat(),'permitted_use':'production','fixture':True}
    data.update(changes)
    return env.client.post(ROOT+'/assets',json=data,headers=env.headers)

def brief(asset, **changes):
    data={'request_id':str(uuid4()),'asset_id':asset,'objective':'Answer a product question','hypothesis':'A clear description may help inquiries',
          'question':'What is shown?','question_source':'hypothesis','question_evidence':'Synthetic engineering fixture',
          'facts':[{'id':'product','text':'Fotografía de prueba.','source':'Test author',
                    'valid_until':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}],
          'caption_fact_ids':['product'],'brand_direction':'Natural photo, no overlay','reference_reason':'Photo-first fixture',
          'primary_measure':'qualified_inquiries','confirmed':True}
    data.update(changes)
    return data

def create(env):
    uploaded=photo(env)
    assert uploaded.status_code==200,uploaded.text
    value=brief(uploaded.json()['id'])
    response=env.client.post(ROOT+'/packs',json=value,headers=env.headers)
    assert response.status_code==200,response.text
    return value,response.json()

def assessment_payload(pack, outcome='ready', **changes):
    result={'request_id':str(uuid4()),'digest':pack['digest'],'outcome':outcome,
            'reason':'Engineering fixture reviewer checked the full output',
            **{key:{'verdict':'acceptable','reason':''} for key in ('technical','factual','craft','brand_fit','purpose')}}
    result.update(changes)
    return result


def approval(env,pack):
    route=ROOT+'/packs/'+pack['id']
    reviews=env.client.get(route+'/reviews')
    review_id=None
    if reviews.status_code==200 and reviews.json()['digest']==pack['digest'] and not pack.get('stale'):
        existing=[e for e in reviews.json()['events'] if e['kind']=='assessment']
        if existing: review_id=existing[-1]['id']
        else:
            saved=env.client.post(route+'/reviews',json=assessment_payload(pack),headers=env.headers)
            if saved.status_code==200: review_id=saved.json()['id']
    return env.client.post(route+'/approve',headers=env.headers,json={'digest':pack['digest'],'review_id':review_id})

def test_real_upload_edit_approve_export(social):
    value,pack=create(social)
    route=ROOT+'/packs/'+pack['id']
    repeated=social.client.post(ROOT+'/packs',json=value,headers=social.headers)
    assert repeated.json()['id']==pack['id']
    assert repeated.json()['revision']==1
    assert social.client.get(route+'/export').status_code==409
    assert approval(social,pack).status_code==200
    assert approval(social,pack).status_code==200
    output=social.client.get(route+'/export')
    assert output.status_code==200
    with zipfile.ZipFile(io.BytesIO(output.content)) as archive:
        assert Image.open(io.BytesIO(archive.read('post.jpg'))).size==(1080,1350)
        assert archive.read('caption.txt').decode()=='Fotografía de prueba.'
        assert json.loads(archive.read('measurement.json'))['value'] is None
    value.update(expected_revision=1,focal_x=.2)
    revised=social.client.put(route,json=value,headers=social.headers)
    assert revised.status_code==200,revised.text
    assert not revised.json()['approved']
    assert approval(social,pack).status_code==409
    assert social.client.get(route+'/export').status_code==409
    assert social.client.put(route,json=value,headers=social.headers).status_code==409
    assert approval(social,revised.json()).status_code==200

def test_scope_csrf_rights_expiry_and_source_deletion(social):
    value,pack=create(social)
    assert social.client.get(ROOT.replace(BUSINESS,OTHER)+'/packs/'+pack['id']).status_code in (403,404)
    assert social.client.post(ROOT+'/packs',json=value).status_code==403
    reference=photo(social,permitted_use='reference_only').json()
    assert social.client.post(ROOT+'/packs',json=brief(reference['id']),headers=social.headers).status_code==409
    value['facts'][0]['valid_until']='2000-01-01T00:00:00Z'
    assert social.client.post(ROOT+'/packs',json=value,headers=social.headers).status_code==409
    assert approval(social,pack).status_code==200
    assert social.client.delete(ROOT+'/assets/'+value['asset_id'],headers=social.headers).status_code==200
    stale=social.client.get(ROOT+'/packs/'+pack['id'])
    assert stale.status_code==200 and stale.json()['stale'] and not stale.json()['media_available']
    for ending in ('/image','/export'):
        assert social.client.get(ROOT+'/packs/'+pack['id']+ending).status_code==409

def test_invalid_material_and_unresolved_claims(social):
    assert photo(social,data_base64='garbage').status_code==422
    value,pack=create(social)
    value['caption_fact_ids']=['invented_price']
    assert social.client.post(ROOT+'/packs',json=value,headers=social.headers).status_code==422
    value['caption_fact_ids']=['product']
    value['facts'][0]['text']='Buy [product] now'
    assert social.client.post(ROOT+'/packs',json=value,headers=social.headers).status_code==422
    assert social.client.get(ROOT).json()['baseline']['reach'] is None
