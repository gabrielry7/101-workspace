"""Delivery-only contracts. SES does not document SendEmail idempotency."""
from dataclasses import dataclass
from typing import Protocol
import base64
import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Submission:
    state: str  # accepted / rejected / retryable (known not accepted) / unknown
    message_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class Message:
    key: str
    sender: str
    destination: str
    subject: str
    html: str
    text: str
    unsubscribe_url: str
    template: dict | None = None


class Transport(Protocol):
    name: str
    capabilities: dict
    def validate(self) -> list[str]: ...
    def submit(self, message: Message) -> Submission: ...
    def verify_event(self, body: bytes, signature: str | None) -> dict: ...


class FakeTransport:
    name = 'simulated_email'
    capabilities = {'idempotency': True, 'delivery_receipts': True, 'read_events': False, 'network': False}

    def __init__(self, secret='test-only-callback-secret'):
        self.secret = secret
        self.messages = {}

    def validate(self):
        return []

    def submit(self, message):
        self.messages.setdefault(message.key, message)
        return Submission('accepted', 'sim-' + message.key)

    def verify_event(self, body, signature):
        expected = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            raise ValueError('invalid_callback_signature')
        return json.loads(body)


class SESTransport:
    name = 'ses'
    capabilities = {'idempotency': False, 'delivery_receipts': True, 'read_events': False, 'network': True}

    def __init__(self, client, *, sender, configuration_set, topic_arn, certificate_fetcher=None):
        self.client = client
        self.sender = sender
        self.configuration_set = configuration_set
        self.topic_arn = topic_arn
        self.certificate_fetcher = certificate_fetcher or self._certificate

    @classmethod
    def from_environment(cls, **configuration):
        # Use the existing environment/AWS credential chain; never persist credentials.
        import boto3
        from botocore.config import Config
        return cls(boto3.client('sesv2', config=Config(connect_timeout=5, read_timeout=15,
            retries={'total_max_attempts': 1})), **configuration)

    def validate(self):
        problems = []
        if not self.configuration_set or not re.fullmatch(r'arn:aws:sns:[a-z0-9-]+:\d{12}:[A-Za-z0-9_-]+', self.topic_arn):
            problems.append('ses_event_destination_unconfigured')
        if not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', self.sender):
            problems.append('sender_invalid')
        return problems

    def readiness(self):
        """Explicit read-only activation check, never called by simulation."""
        account = self.client.get_account()
        identity = self.client.get_email_identity(EmailIdentity=self.sender.split('@')[1])
        return {'production_access': account.get('ProductionAccessEnabled') is True,
                'sending_enabled': account.get('SendingEnabled') is True,
                'verified': identity.get('VerifiedForSendingStatus') is True,
                'dkim': identity.get('DkimAttributes', {}).get('Status') == 'SUCCESS',
                'mail_from': identity.get('MailFromAttributes', {}).get('MailFromDomainStatus'),
                'dmarc': 'requires_dns_review'}

    def submit(self, message):
        if self.validate() or message.sender != self.sender or not message.unsubscribe_url.startswith('https://'):
            return Submission('rejected', reason='sender_or_unsubscribe_configuration')
        try:
            result = self.client.send_email(FromEmailAddress=message.sender,
                Destination={'ToAddresses': [message.destination]},
                ConfigurationSetName=self.configuration_set,
                EmailTags=[{'Name': 'delivery_key', 'Value': message.key}],
                Content={'Simple': {'Subject': {'Data': message.subject, 'Charset': 'UTF-8'},
                    'Body': {'Html': {'Data': message.html, 'Charset': 'UTF-8'},
                             'Text': {'Data': message.text, 'Charset': 'UTF-8'}},
                    'Headers': [{'Name': 'List-Unsubscribe', 'Value': '<' + message.unsubscribe_url + '>'},
                                {'Name': 'List-Unsubscribe-Post', 'Value': 'List-Unsubscribe=One-Click'}]}})
            return Submission('accepted', result['MessageId'])
        except Exception as exc:
            code = getattr(exc, 'response', {}).get('Error', {}).get('Code', '')
            if code in {'TooManyRequestsException', 'LimitExceededException'}:
                return Submission('retryable', reason=code)
            if code in {'MessageRejected', 'MailFromDomainNotVerifiedException', 'AccountSuspendedException',
                        'SendingPausedException', 'BadRequestException', 'NotFoundException', 'AccessDeniedException'}:
                return Submission('rejected', reason=code)
            # Timeout, connection loss, 5xx or malformed success can follow acceptance.
            return Submission('unknown', reason='ses_submission_outcome_unknown')

    def _certificate(self, url):
        import httpx
        # URL checked below; no redirects, bounded bytes and TLS verification enabled.
        with httpx.stream('GET', url, timeout=5, follow_redirects=False) as response:
            response.raise_for_status()
            data = b''
            for chunk in response.iter_bytes():
                data += chunk
                if len(data) > 32768:
                    raise ValueError('certificate_too_large')
            return data

    def verify_event(self, body, signature=None):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        data = json.loads(body)
        if data.get('TopicArn') != self.topic_arn or data.get('Type') != 'Notification' or data.get('SignatureVersion') != '2':
            raise ValueError('unexpected_sns_integration_or_signature_version')
        region = self.topic_arn.split(':')[3]
        url = data['SigningCertURL']
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.netloc != f'sns.{region}.amazonaws.com'
                or parsed.query or parsed.fragment or not re.fullmatch(r'/SimpleNotificationService-[A-Za-z0-9]+\.pem', parsed.path)):
            raise ValueError('untrusted_sns_certificate_url')
        keys = ['Message', 'MessageId'] + (['Subject'] if 'Subject' in data else []) + ['Timestamp', 'TopicArn', 'Type']
        canonical = ''.join(k + '\n' + data[k] + '\n' for k in keys).encode()
        cert = x509.load_pem_x509_certificate(self.certificate_fetcher(url))
        now = datetime.now(timezone.utc)
        if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
            raise ValueError('expired_signing_certificate')
        cert.public_key().verify(base64.b64decode(data['Signature'], validate=True), canonical, padding.PKCS1v15(), hashes.SHA256())
        event = json.loads(data['Message'])
        mail = event['mail']
        if mail['source'] != self.sender:
            raise ValueError('unexpected_sender')
        kind = {'Send': 'accepted', 'Delivery': 'delivered', 'Bounce': 'bounced',
                'Complaint': 'complaint', 'Reject': 'rejected', 'DeliveryDelay': 'delayed'}.get(event.get('eventType'))
        if not kind:
            raise ValueError('unsupported_ses_event')
        event_time = event.get(event['eventType'][0].lower()+event['eventType'][1:], {}).get('timestamp', mail['timestamp'])
        return {'id': data['MessageId'], 'key': mail['tags']['delivery_key'][0],
                'message_id': mail['messageId'], 'kind': kind, 'at': event_time}
