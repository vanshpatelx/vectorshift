import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import base64
import urllib.parse

import requests
from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

CLIENT_ID = '5ac13f32-1d75-4e62-8d64-00530c69ef12'
CLIENT_SECRET = '3dccd09e-f643-4dfa-a486-d8ba6ea1ceea'
SCOPES = 'oauth crm.objects.companies.read'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'

authorization_url = (
    f"https://app.hubspot.com/oauth/authorize?client_id={urllib.parse.quote(CLIENT_ID)}"
    f"&scope={urllib.parse.quote(SCOPES)}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
)

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600) # 10m
    return f'{authorization_url}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description'))
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')

    if not encoded_state:
        raise HTTPException(status_code=400, detail='Missing state parameter.')

    try:
        state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))
    except (json.JSONDecodeError, base64.binascii.Error):
        raise HTTPException(status_code=400, detail='Invalid state format.')

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state:
        raise HTTPException(status_code=400, detail='State not found in Redis.')

    try:
        saved_state = json.loads(base64.urlsafe_b64decode(saved_state).decode('utf-8'))
    except (json.JSONDecodeError, base64.binascii.Error):
        raise HTTPException(status_code=400, detail='Invalid state format in Redis.')

    if original_state != saved_state.get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                'https://api.hubspot.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': REDIRECT_URI,
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                },
                headers={
                    'content-type': 'application/x-www-form-urlencoded',
                    'accept': 'application/json'
                }
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)

    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')

    try:
        credentials = json.loads(credentials)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid credentials format.')

    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
    return credentials

def create_integration_item_metadata_object(
    response_json: str, item_type: str, parent_id=None, parent_name=None
) -> IntegrationItem:
    parent_id = None if parent_id is None else parent_id + '_Base'
    integration_item_metadata = IntegrationItem(
        id=response_json.get('id', None) + '_' + item_type,
        name=response_json.get('properties', None).get('name', None),
        domain=response_json.get('properties', None).get('domain', None),
        type=item_type,
        parent_id=parent_id,
        parent_path_or_name=parent_name,
    )
    return integration_item_metadata

def fetch_items(
    access_token: str, url: str, aggregated_response: list, limit=None
) -> dict:
    params = {'limit': limit} if limit is not None else {}
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers, params=params)
 
    if response.status_code == 200:
        results = response.json().get('results', {})
        limit = response.json().get('limit', None)

        for item in results:
            aggregated_response.append(item)

        if limit is not None:
            fetch_items(access_token, url, aggregated_response, limit)
        else:
            return
    else: print("erro")

async def get_items_hubspot(credentials):
    credentials = json.loads(credentials)
    url = 'https://api.hubapi.com/crm/v3/objects/companies'
    list_of_integration_item_metadata = []
    list_of_responses = []

    fetch_items(credentials.get('access_token'), url, list_of_responses)

    for response in list_of_responses:
        list_of_integration_item_metadata.append(
            create_integration_item_metadata_object(response, 'hubspot_company')
        )

    return list_of_integration_item_metadata
