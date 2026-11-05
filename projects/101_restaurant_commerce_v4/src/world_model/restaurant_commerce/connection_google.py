"""Narrow read-only Google Business Profile adapter. No listing or review writes."""
import base64
import hashlib
import json
import re
from datetime import timedelta
from urllib.parse import urlencode
import httpx

SCOPE = 'https://www.googleapis.com/auth/business.manage'
METRICS = ['WEBSITE_CLICKS', 'CALL_CLICKS', 'BUSINESS_DIRECTION_REQUESTS']
MASK = 'name,title,storefrontAddress,websiteUri,phoneNumbers,regularHours,metadata'


class ConnectionFailure(Exception):
    def __init__(self, reason, retry=False):
        self.reason, self.retry = reason, retry
        super().__init__(reason)


def resource(value, kind):
    if not re.fullmatch(kind + r'/[0-9]+', value or ''):
        raise ConnectionFailure('invalid_provider_resource')
    return value


def location_key(account, location):
    return resource(account, 'accounts') + '/' + resource(location, 'locations')


class GoogleBusinessAdapter:
    mode = 'live'

    def __init__(self, client_id, client_secret, redirect_uri, *, transport=None):
        self.client_id, self.client_secret, self.redirect_uri = client_id, client_secret, redirect_uri
        self.transport = transport

    def authorize_url(self, state, verifier):
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(dict(
            client_id=self.client_id, redirect_uri=self.redirect_uri, response_type='code',
            scope=SCOPE, access_type='offline', prompt='consent', state=state,
            code_challenge=challenge, code_challenge_method='S256'))

    def request(self, method, url, *, tokens=None, data=None, params=None):
        # All URL origins and paths originate in this adapter, never in a callback.
        try:
            with httpx.Client(transport=self.transport, timeout=12, follow_redirects=False, trust_env=False) as client:
                with client.stream(method, url, data=data, params=params,
                                   headers={'Authorization': 'Bearer ' + tokens['access_token']} if tokens else {}) as response:
                    raw = bytearray()
                    for part in response.iter_bytes():
                        raw.extend(part)
                        if len(raw) > 2_000_000:
                            raise ConnectionFailure('provider_response_too_large')
                    status = response.status_code
                    if url == 'https://oauth2.googleapis.com/revoke' and status == 400:
                        try:
                            if json.loads(raw).get('error') == 'invalid_token':
                                return {}  # Already revoked; idempotent terminal result.
                        except (ValueError, AttributeError):
                            pass
                    if status == 429 or status >= 500:
                        raise ConnectionFailure('provider_temporarily_unavailable', retry=True)
                    if status == 401:
                        raise ConnectionFailure('reconnect_required')
                    if status == 403:
                        raise ConnectionFailure('provider_access_denied')
                    if not 200 <= status < 300:
                        raise ConnectionFailure('provider_request_rejected')
                    result = json.loads(raw) if raw else {}
                    if not isinstance(result, dict):
                        raise ValueError()
                    return result
        except (httpx.HTTPError, OSError) as exc:
            raise ConnectionFailure('provider_network_error', retry=True) from exc
        except (ValueError, KeyError) as exc:
            raise ConnectionFailure('invalid_provider_response') from exc

    def _token(self, data, now, previous=None):
        response = self.request('POST', 'https://oauth2.googleapis.com/token', data={
            **data, 'client_id': self.client_id, 'client_secret': self.client_secret})
        if not isinstance(response.get('access_token'), str) or response.get('token_type', '').lower() != 'bearer':
            raise ConnectionFailure('invalid_token_response')
        scopes = response.get('scope', (previous or {}).get('scope', ''))
        if SCOPE not in scopes.split():
            raise ConnectionFailure('required_permission_missing')
        refresh = response.get('refresh_token', (previous or {}).get('refresh_token'))
        if not refresh:
            raise ConnectionFailure('offline_access_missing')
        try:
            lifetime = min(86400, max(1, int(response['expires_in'])))
        except (ValueError, KeyError, TypeError) as exc:
            raise ConnectionFailure('invalid_token_response') from exc
        return {'access_token': response['access_token'], 'refresh_token': refresh,
                'scope': scopes, 'expires_at': (now + timedelta(seconds=lifetime)).timestamp()}

    def exchange(self, code, verifier, now):
        return self._token({'code': code, 'code_verifier': verifier, 'redirect_uri': self.redirect_uri,
                            'grant_type': 'authorization_code'}, now)

    def refresh(self, tokens, now):
        if tokens['expires_at'] > now.timestamp() + 60:
            return tokens
        try:
            return self._token({'refresh_token': tokens['refresh_token'], 'grant_type': 'refresh_token'}, now, tokens)
        except ConnectionFailure as exc:
            if exc.reason == 'provider_request_rejected':
                raise ConnectionFailure('reconnect_required') from exc
            raise

    def pages(self, url, field, tokens, params=None):
        result, seen = [], set()
        for _ in range(20):
            response = self.request('GET', url, tokens=tokens, params=params)
            if not isinstance(response.get(field, []), list):
                raise ConnectionFailure('invalid_provider_response')
            result.extend(response.get(field, []))
            cursor = response.get('nextPageToken')
            if not cursor:
                return result
            if cursor in seen:
                raise ConnectionFailure('pagination_cycle')
            seen.add(cursor)
            params = {**(params or {}), 'pageToken': cursor}
        raise ConnectionFailure('account_selection_limit')

    def discover(self, tokens):
        accounts = self.pages('https://mybusinessaccountmanagement.googleapis.com/v1/accounts', 'accounts', tokens, {'pageSize': 20})
        if len(accounts) > 20:
            raise ConnectionFailure('account_selection_limit')
        assets = []
        for account in accounts:
            aid = resource(account.get('name'), 'accounts')
            locations = self.pages('https://mybusinessbusinessinformation.googleapis.com/v1/' + aid + '/locations',
                                   'locations', tokens, {'readMask': MASK, 'pageSize': 100})
            for location in locations:
                assets.append({'key': location_key(aid, location.get('name')), 'account': account, 'location': location})
                if len(assets) > 500:
                    raise ConnectionFailure('account_selection_limit')
        return assets

    def snapshot(self, tokens, selected, now):
        parts = selected.split('/')
        if len(parts) != 4:
            raise ConnectionFailure('invalid_provider_resource')
        account, location = '/'.join(parts[:2]), '/'.join(parts[2:])
        location_key(account, location)
        listing = self.request('GET', 'https://mybusinessbusinessinformation.googleapis.com/v1/' + location,
                               tokens=tokens, params={'readMask': MASK})
        # Preserve original response pages; no stored aggregation. Limit review
        # display to the latest page and state coverage explicitly.
        sections, errors = {'listing': listing}, {}
        end = now.date() - timedelta(days=3)
        start = end - timedelta(days=27)
        params = [('dailyMetrics', metric) for metric in METRICS]
        for name, date in [('startDate', start), ('endDate', end)]:
            params += [('dailyRange.' + name + '.' + field, str(getattr(date, field))) for field in ['year', 'month', 'day']]
        calls = {
            'reviews': ('https://mybusiness.googleapis.com/v4/' + selected + '/reviews', {'pageSize': 50, 'orderBy': 'updateTime desc'}),
            'metrics': ('https://businessprofileperformance.googleapis.com/v1/' + location + ':fetchMultiDailyMetricsTimeSeries', params),
        }
        for name, (url, query) in calls.items():
            try:
                sections[name] = self.request('GET', url, tokens=tokens, params=query)
            except ConnectionFailure as exc:
                if exc.reason == 'reconnect_required':
                    raise
                errors[name] = exc.reason
        return {'sections': sections, 'errors': errors, 'period': {'start': start.isoformat(), 'end': end.isoformat()},
                'review_coverage': 'latest_page_up_to_50', 'source': 'google_business_profile'}

    def revoke(self, tokens):
        self.request('POST', 'https://oauth2.googleapis.com/revoke', data={'token': tokens['refresh_token']})


class FakeGoogleBusinessAdapter:
    mode = 'test'

    def authorize_url(self, state, verifier):
        return '/connections/demo-authorize?' + urlencode({'state': state})

    def exchange(self, code, verifier, now):
        if code != 'synthetic-owner-grant':
            raise ConnectionFailure('provider_request_rejected')
        return {'access_token': 'synthetic-access', 'refresh_token': 'synthetic-refresh', 'scope': SCOPE,
                'expires_at': (now + timedelta(hours=1)).timestamp()}

    def refresh(self, tokens, now):
        return {**tokens, 'expires_at': (now + timedelta(hours=1)).timestamp()}

    def discover(self, tokens):
        return [{'key': 'accounts/101/locations/' + number, 'account': {'name': 'accounts/101', 'accountName': 'Cuenta ficticia'},
                 'location': {'name': 'locations/' + number, 'title': title,
                              'storefrontAddress': {'addressLines': ['Dirección de demostración'], 'locality': 'Bogotá'}}}
                for number, title in [('1001', 'Honorato · ubicación ficticia'), ('1002', 'Segunda ubicación ficticia')]]

    def snapshot(self, tokens, selected, now):
        listing = next((a['location'] for a in self.discover(tokens) if a['key'] == selected), None)
        if listing is None:
            raise ConnectionFailure('provider_access_denied')
        date = now.date() - timedelta(days=3)
        return {'sections': {'listing': listing,
            'reviews': {'reviews': [{'reviewId': 'synthetic-review', 'reviewer': {'displayName': 'Cliente ficticio'},
                                    'starRating': 'FIVE', 'comment': 'Reseña de prueba. No describe una experiencia real.',
                                    'updateTime': now.isoformat(), 'reviewReply': {'comment': 'Respuesta de demostración.'}}],
                        'totalReviewCount': 1, 'averageRating': 5},
            'metrics': {'multiDailyMetricTimeSeries': [{'dailyMetricTimeSeries': [
                {'dailyMetric': metric, 'timeSeries': {'datedValues': [{'date': {'year': date.year, 'month': date.month, 'day': date.day}, 'value': str(value)}]}}
                for metric, value in zip(METRICS, [12, 4, 7])]}]}},
            'errors': {}, 'period': {'start': date.isoformat(), 'end': date.isoformat()},
            'review_coverage': 'synthetic_one_review', 'source': 'simulated_google_business_profile'}

    def revoke(self, tokens):
        pass
