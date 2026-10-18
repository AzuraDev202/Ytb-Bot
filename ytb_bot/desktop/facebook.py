"""Small fixed-host Messenger client; tokens never enter URLs or public errors."""
import datetime as dt
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlencode, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

GRAPH_VERSION = 'v25.0'
TEXT_LIMIT = 2000


class FacebookRejected(ValueError):
    """The provider explicitly rejected the request."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def graph_request(method, path, token, params=None, payload=None):
    url = f'https://graph.facebook.com/{GRAPH_VERSION}/{path}'
    if params:
        url += '?' + urlencode(params)
    request = Request(url, method=method, headers={'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'}, data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with build_opener(NoRedirect).open(request, timeout=25) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Response too large')
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError('Invalid response')
        if 'error' in value:
            raise FacebookRejected('Meta rejected the request. Check Page permissions, token expiry and messaging eligibility.')
        return value
    except FacebookRejected:
        raise
    except HTTPError as error:
        if 400 <= error.code < 500:
            raise FacebookRejected('Meta rejected the request. Check Page permissions, token expiry and messaging eligibility.') from None
        raise ValueError('Meta response is uncertain. Check the Page inbox before trying again.') from None
    except Exception:
        raise ValueError('Unable to verify the Meta response. Check the Page inbox before trying again.') from None


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_:.\-]{1,256}', value):
        raise ValueError('Invalid Facebook identifier.')
    return quote(value, safe='')


def within_window(timestamp):
    try:
        latest = dt.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return 0 <= (dt.datetime.now(dt.timezone.utc) - latest).total_seconds() < 24 * 3600
    except (AttributeError, TypeError, ValueError):
        return False


class FacebookClient:
    def __init__(self, request=None):
        self.request = request or graph_request

    def _list(self, path, token, params):
        rows, seen = [], set()
        params = dict(params, limit=100)
        for _ in range(20):
            value = self.request('GET', path, token, params=params)
            if not isinstance(value.get('data'), list):
                raise ValueError('Unable to verify Facebook conversation history.')
            rows.extend(value['data'])
            paging = value.get('paging', {})
            if not paging.get('next'):
                return rows
            cursor = paging.get('cursors', {}).get('after')
            if not isinstance(cursor, str) or not cursor or len(cursor) > 4096 or cursor in seen:
                break
            seen.add(cursor)
            params['after'] = cursor
        raise ValueError('Conversation history is incomplete. Narrow the Page inbox before retrying.')

    def page(self, token):
        value = self.request('GET', 'me', token, params={'fields': 'id,name,category'})
        if not value.get('category') or not value.get('name'):
            raise ValueError('Use a Page access token, not a personal account token.')
        page_id = identifier(value.get('id'))
        self.request('GET', page_id + '/conversations', token,
                     params={'platform': 'messenger', 'fields': 'id', 'limit': 1})
        return {'id': value['id'], 'name': value['name']}

    def conversations(self, token, page_id):
        rows = self._list(identifier(page_id) + '/conversations', token,
                          {'platform': 'messenger', 'fields': 'id,participants'})
        result = []
        for row in rows:
            conversation = self._conversation(token, page_id, row)
            if conversation:
                result.append(conversation)
        return result

    def _conversation(self, token, page_id, row):
        participants = row.get('participants', {})
        people = participants.get('data', [])
        if participants.get('paging', {}).get('next') or len(people) != 2:
            return None
        if sum(person.get('id') == page_id for person in people) != 1:
            return None
        person = next(person for person in people if person.get('id') != page_id)
        recipient_id = person.get('id')
        conversation_id = row.get('id')
        identifier(recipient_id)
        identifier(conversation_id)
        eligible = False
        last_inbound = ''
        try:
            messages = self._list(identifier(conversation_id) + '/messages', token, {'fields': 'from,created_time'})
            inbound = [dt.datetime.fromisoformat(message['created_time'].replace('Z', '+00:00'))
                       for message in messages if message.get('from', {}).get('id') == recipient_id]
            if inbound:
                last_inbound = max(inbound).isoformat()
                eligible = within_window(last_inbound)
        except (ValueError, KeyError, TypeError):
            eligible = False
        return {'id': conversation_id, 'recipient_id': recipient_id,
                'name': person.get('name') or recipient_id, 'eligible': eligible, 'last_inbound': last_inbound}

    def recipient(self, token, page_id, recipient_id, conversation_id=None):
        if conversation_id:
            row = self.request('GET', identifier(conversation_id), token, params={'fields': 'id,participants'})
            conversation = self._conversation(token, page_id, row)
            if conversation and conversation['recipient_id'] == recipient_id and conversation['id'] == conversation_id:
                return conversation
            raise ValueError('The recipient is not in a verified Page conversation.')
        for conversation in self.conversations(token, page_id):
            if conversation['recipient_id'] == recipient_id:
                return conversation
        raise ValueError('The recipient is not in a verified Page conversation.')

    def send(self, token, page_id, recipient_id, body):
        value = self.request('POST', identifier(page_id) + '/messages', token, payload={
            'recipient': {'id': recipient_id}, 'messaging_type': 'RESPONSE', 'message': {'text': body}})
        if value.get('recipient_id') != recipient_id or not isinstance(value.get('message_id'), str) or not value['message_id']:
            raise ValueError('Messenger acceptance could not be verified.')
        return value['message_id']
