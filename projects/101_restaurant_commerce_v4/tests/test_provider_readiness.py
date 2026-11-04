"""Account probes are explicit, account-bound, evidence-retaining and never send."""
import json
from datetime import timedelta
from unittest.mock import Mock
import pytest
from sqlalchemy import select,func
from test_whatsapp_campaigns import wa,env,factory
from world_model.restaurant_commerce import whatsapp as w
from world_model.restaurant_commerce.campaign_demo import BUSINESS,OTHER,CLOCK
from world_model.restaurant_commerce.campaign_models import CampaignSettings,WhatsAppSender,WhatsAppEvidence

ROOT='/api/operator/restaurants/'+BUSINESS+'/campaigns/provider-readiness'


@pytest.fixture
def provider(wa):
    a=Mock();a.name='whatsapp_cloud';a.phone_id=wa.wa.phone_id;a.waba_id=wa.wa.waba_id;a.validate.return_value=[]
    a.account_readiness.return_value={'phone':{'id':a.phone_id,'quality_rating':'GREEN'},'templates':[],
        'templates_complete':True,'phone_waba_binding_verified':True,'phone_catalogue_complete':True}
    with wa.factory() as s:
        cfg=s.get(CampaignSettings,BUSINESS);cfg.scope='provider_test';s.commit()
        values=json.loads(s.get(WhatsAppSender,BUSINESS).document);values['link_origin']='https://example.test'
        w.configure(s,BUSINESS,w.SenderInput(**values),CLOCK)
    wa.options['integrations']['official']={'business_id':BUSINESS,'scope':'provider_test','adapter':a}
    return wa,a


def test_page_load_never_probes_and_explicit_probe_retains_truth(provider):
    e,a=provider
    assert e.client.get(ROOT).status_code==200;a.account_readiness.assert_not_called()
    r=e.client.post(ROOT+'/whatsapp/probe',headers=e.headers);assert r.status_code==200,r.text
    state=r.json()['channels']['whatsapp'];assert state['provider_observed_at']==CLOCK.isoformat()
    assert 'phone_waba_binding_not_verified' not in state['blockers']
    assert 'current_account_allowance_review_required' in state['blockers']
    with e.factory() as s:
        doc=json.loads(s.get(WhatsAppSender,BUSINESS).document)
        assert doc['status']=='UNVERIFIED' and doc['allowance']==0 and doc['provider_account_binding'] is True
        assert s.scalar(select(func.count()).select_from(WhatsAppEvidence).where(WhatsAppEvidence.kind=='provider_sync'))==1
    a.submit.assert_not_called()


@pytest.mark.parametrize('field',['phone_waba_binding_verified','phone_catalogue_complete','templates_complete'])
def test_incomplete_probe_cannot_record_readiness(provider,field):
    e,a=provider;a.account_readiness.return_value[field]=False
    assert e.client.post(ROOT+'/whatsapp/probe',headers=e.headers).status_code==409
    with e.factory() as s:assert 'provider_observed_at' not in json.loads(s.get(WhatsAppSender,BUSINESS).document)
    a.submit.assert_not_called()


def test_foreign_account_and_cross_business_block_before_network(provider):
    e,a=provider;a.waba_id='999999999'
    assert e.client.post(ROOT+'/whatsapp/probe',headers=e.headers).status_code==409
    assert e.client.post(ROOT.replace(BUSINESS,OTHER)+'/whatsapp/probe',headers=e.headers).status_code==403
    assert e.client.post(ROOT+'/whatsapp/probe').status_code==403
    a.account_readiness.assert_not_called()
