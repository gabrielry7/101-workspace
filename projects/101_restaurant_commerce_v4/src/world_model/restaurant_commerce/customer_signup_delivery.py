"""Transactional phone verification, separate from marketing delivery."""
import hashlib
import hmac
import re
from dataclasses import dataclass
import httpx


@dataclass(frozen=True)
class VerificationResult:
    state: str  # pending, approved, denied, rejected, unknown
    provider_id: str | None = None


class FakePhoneVerifier:
    name = 'simulated_phone_verification'
    network = False

    def __init__(self, secret='synthetic-signup-verification-only'):
        self.secret = secret
        self.calls = []

    def validate(self):
        return []

    def code(self, provider_id):
        raw = hmac.new(self.secret.encode(), provider_id.encode(), hashlib.sha256).digest()
        return str(int.from_bytes(raw[:4], 'big') % 1_000_000).zfill(6)

    def start(self, phone, nonce):
        self.calls.append(phone)
        return VerificationResult('pending', 'demo-' + nonce)

    def check(self, phone, provider_id, code):
        return VerificationResult('approved' if hmac.compare_digest(self.code(provider_id), code) else 'denied', provider_id)


class TwilioPhoneVerifier:
    name = 'twilio_verify'
    network = True

    def __init__(self, account_sid, auth_token, service_sid, *, client=None):
        self.account_sid, self.auth_token, self.service_sid = account_sid, auth_token, service_sid
        self.client = client or httpx.Client(timeout=12, follow_redirects=False, trust_env=False)

    @classmethod
    def from_environment(cls):
        import os
        return cls(*(os.getenv('SIGNUP_TWILIO_' + name, '') for name in ['ACCOUNT_SID', 'AUTH_TOKEN', 'SERVICE_SID']))

    def validate(self):
        return [] if (re.fullmatch(r'AC[0-9a-fA-F]{32}', self.account_sid) and self.auth_token
                      and re.fullmatch(r'VA[0-9a-fA-F]{32}', self.service_sid)) else ['verification_unconfigured']

    def _call(self, resource, fields, phone, expected_id=None):
        if self.validate():
            return VerificationResult('rejected')
        try:
            response = self.client.post(f'https://verify.twilio.com/v2/Services/{self.service_sid}/{resource}',
                                        auth=(self.account_sid, self.auth_token), data=fields)
            if 400 <= response.status_code < 500:
                return VerificationResult('rejected')
            if response.status_code not in {200, 201}:
                return VerificationResult('unknown')
            data = response.json()
            if (data.get('account_sid') != self.account_sid or data.get('service_sid') != self.service_sid
                    or data.get('to') != phone or data.get('channel') != 'sms'
                    or not re.fullmatch(r'VE[0-9a-fA-F]{32}', data.get('sid', ''))
                    or (expected_id and data['sid'] != expected_id)):
                return VerificationResult('unknown')
            if resource == 'Verifications':
                return VerificationResult('pending', data['sid']) if data.get('status') == 'pending' else VerificationResult('unknown')
            return VerificationResult('approved' if data.get('status') == 'approved' else 'denied', data['sid'])
        except Exception:
            return VerificationResult('unknown')

    def start(self, phone, nonce):
        # No provider idempotency claim; a timeout is not automatically resent.
        return self._call('Verifications', {'To': phone, 'Channel': 'sms', 'Locale': 'es'}, phone)

    def check(self, phone, provider_id, code):
        return self._call('VerificationCheck', {'VerificationSid': provider_id, 'Code': code}, phone, provider_id)


class SesEmailVerifier:
    """Reuse SESv2/AWS credentials; transactional codes, never marketing headers."""
    name = 'ses_email_verification'
    network = True

    def __init__(self, client, *, sender, configuration_set, code_secret):
        self.client, self.sender, self.configuration_set = client, sender, configuration_set
        self.code_secret = code_secret

    @classmethod
    def from_environment(cls, *, sender, configuration_set):
        import os
        import boto3
        from botocore.config import Config
        return cls(boto3.client('sesv2', config=Config(connect_timeout=5, read_timeout=12,
                   retries={'total_max_attempts': 1})), sender=sender,
                   configuration_set=configuration_set, code_secret=os.getenv('SIGNUP_EMAIL_CODE_SECRET', ''))

    def validate(self):
        return [] if (len(self.code_secret) >= 32 and self.configuration_set
                      and re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', self.sender)) else ['email_verification_unconfigured']

    def code(self, destination, nonce):
        value = hmac.new(self.code_secret.encode(), (destination + ':' + nonce).encode(), hashlib.sha256).digest()
        return str(int.from_bytes(value[:4], 'big') % 1_000_000).zfill(6)

    def start(self, destination, nonce):
        if self.validate():
            return VerificationResult('rejected')
        code = self.code(destination, nonce)
        text = f'Tu código de acceso a 101 es {code}. Vence en 10 minutos. No lo compartas. Si no lo solicitaste, ignora este correo.'
        try:
            result = self.client.send_email(FromEmailAddress=self.sender, Destination={'ToAddresses': [destination]},
                ConfigurationSetName=self.configuration_set, EmailTags=[{'Name': 'signup_challenge', 'Value': nonce}],
                Content={'Simple': {'Subject': {'Data': 'Tu código para entrar · 101', 'Charset': 'UTF-8'},
                    'Body': {'Text': {'Data': text, 'Charset': 'UTF-8'},
                             'Html': {'Data': f'<html lang="es"><body><h1>Tu código de acceso</h1><p>{code}</p><p>Vence en 10 minutos. No lo compartas.</p><p>Si no lo solicitaste, ignora este correo.</p></body></html>', 'Charset': 'UTF-8'}}}})
            return VerificationResult('pending', nonce) if result.get('MessageId') else VerificationResult('unknown')
        except Exception as exc:
            code = getattr(exc, 'response', {}).get('Error', {}).get('Code', '')
            return VerificationResult('rejected' if code in {'MessageRejected', 'BadRequestException', 'AccessDeniedException', 'SendingPausedException'} else 'unknown')

    def check(self, destination, provider_id, code):
        # The durable challenge owns expiry, browser binding, attempts and one use.
        return VerificationResult('approved' if hmac.compare_digest(self.code(destination, provider_id), code) else 'denied', provider_id)
