"""SES request/receipt contracts. No AWS calls or deliverability claim."""
import base64
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509.oid import NameOID
from botocore.stub import Stubber
import boto3
from botocore.config import Config
from world_model.restaurant_commerce.campaign_delivery import SESTransport, Message

TOPIC='arn:aws:sns:us-east-1:123456789012:campaigns'
SENDER='owner@example.test'


def message():
    return Message('abc123',SENDER,'recipient@example.test','Hello','<h1>Hello</h1>','Hello','https://example.test/unsubscribe/token')


def test_ses_sdk_request_is_single_recipient_tagged_and_has_both_unsubscribe_headers():
    client=boto3.client('sesv2',region_name='us-east-1',aws_access_key_id='fixture',aws_secret_access_key='fixture',
        config=Config(retries={'total_max_attempts':1}))
    expected={'FromEmailAddress':SENDER,'Destination':{'ToAddresses':['recipient@example.test']},
        'ConfigurationSetName':'campaigns','EmailTags':[{'Name':'delivery_key','Value':'abc123'}],
        'Content':{'Simple':{'Subject':{'Data':'Hello','Charset':'UTF-8'},
            'Body':{'Html':{'Data':'<h1>Hello</h1>','Charset':'UTF-8'},'Text':{'Data':'Hello','Charset':'UTF-8'}},
            'Headers':[{'Name':'List-Unsubscribe','Value':'<https://example.test/unsubscribe/token>'},
                       {'Name':'List-Unsubscribe-Post','Value':'List-Unsubscribe=One-Click'}]}}}
    with Stubber(client) as stub:
        stub.add_response('send_email',{'MessageId':'provider-id'},expected)
        adapter=SESTransport(client,sender=SENDER,configuration_set='campaigns',topic_arn=TOPIC)
        result=adapter.submit(message())
        assert result.state=='accepted' and result.message_id=='provider-id'
        assert adapter.capabilities['idempotency'] is False
        stub.assert_no_pending_responses()


@pytest.mark.parametrize('error,state',[(TimeoutError(),'unknown'),(RuntimeError(),'unknown'),
    ('TooManyRequestsException','retryable'),('MessageRejected','rejected'),('InternalServiceError','unknown')])
def test_ses_failure_classification_never_blindly_retries_timeout(error,state):
    if isinstance(error,str):
        from botocore.exceptions import ClientError
        error=ClientError({'Error':{'Code':error}},'SendEmail')
    client=Mock();client.send_email.side_effect=error
    adapter=SESTransport(client,sender=SENDER,configuration_set='campaigns',topic_arn=TOPIC)
    assert adapter.submit(message()).state==state
    assert client.send_email.call_count==1


def test_readiness_sandbox_is_not_production_ready():
    client=Mock()
    client.get_account.return_value={'ProductionAccessEnabled':False,'SendingEnabled':True}
    client.get_email_identity.return_value={'VerifiedForSendingStatus':True,'DkimAttributes':{'Status':'SUCCESS'}}
    adapter=SESTransport(client,sender=SENDER,configuration_set='campaigns',topic_arn=TOPIC)
    assert adapter.readiness()['production_access'] is False
    client.send_email.assert_not_called()


@pytest.fixture
def signed():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'synthetic SNS signing fixture')])
    now=datetime.now(timezone.utc)
    cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(1).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=1)).sign(key,hashes.SHA256())
    fetch=Mock(return_value=cert.public_bytes(serialization.Encoding.PEM))
    adapter=SESTransport(Mock(),sender=SENDER,configuration_set='campaigns',topic_arn=TOPIC,certificate_fetcher=fetch)
    event={'eventType':'Delivery','mail':{'source':SENDER,'timestamp':now.isoformat(),'messageId':'ses-message',
        'tags':{'delivery_key':['abc123']}},'delivery':{'timestamp':now.isoformat()}}
    envelope={'Message':json.dumps(event),'MessageId':'sns-id','TopicArn':TOPIC,'Type':'Notification',
        'Timestamp':now.isoformat(),'SignatureVersion':'2','SigningCertURL':'https://sns.us-east-1.amazonaws.com/SimpleNotificationService-fixture.pem'}
    canonical=''.join(k+'\n'+envelope[k]+'\n' for k in ['Message','MessageId','Timestamp','TopicArn','Type']).encode()
    envelope['Signature']=base64.b64encode(key.sign(canonical,padding.PKCS1v15(),hashes.SHA256())).decode()
    return adapter,envelope,fetch


def test_sns_verifies_normalizes_delivery(signed):
    adapter,data,fetch=signed
    event=adapter.verify_event(json.dumps(data).encode())
    assert event['kind']=='delivered' and event['key']=='abc123' and event['message_id']=='ses-message'
    assert fetch.call_count==1


@pytest.mark.parametrize('field,value',[('TopicArn','arn:aws:sns:us-east-1:999999999999:wrong'),
    ('SigningCertURL','https://sns.us-east-1.amazonaws.com.attacker.test/cert.pem'),
    ('SigningCertURL','http://169.254.169.254/latest/meta-data'),('SignatureVersion','1'),
    ('MessageId','tampered'),('Type','SubscriptionConfirmation')])
def test_sns_forgery_and_certificate_ssrf_are_rejected(signed,field,value):
    adapter,data,fetch=signed;data[field]=value
    with pytest.raises(Exception):adapter.verify_event(json.dumps(data).encode())
    if field!='MessageId':fetch.assert_not_called()
