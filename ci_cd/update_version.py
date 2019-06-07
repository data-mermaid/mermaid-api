#!/usr/bin/env python

import os
import sys
import requests

usage = '''
Usage: ./update_version.py <env> <app name> <app version>
'''

if len(sys.argv) < 3:
    print(usage)
    raise ValueError('Missing application or version')

OAUTH_TOKEN_URL = 'https://datamermaid.auth0.com/oauth/token'
environment = sys.argv[1]
application = sys.argv[2]
version = sys.argv[3]

client = requests.session()
audience = 'https://dev-api.datamermaid.org'
if environment == 'dev':
    api_url = 'https://dev-api.datamermaid.org/v1/'
elif environment == 'prod':
    api_url = 'https://api.datamermaid.org/v1/'
    audience = 'https://api.datamermaid.org'
else:
    api_url = 'http://localhost:8080/v1/'

version_url = '{}version/'.format(api_url)

# GET ACCESS TOKEN
payload = {
    "client_id": os.environ.get('CIRCLE_CI_CLIENT_ID'),
    "client_secret": os.environ.get('CIRCLE_CI_CLIENT_SECRET'),
    "audience": audience,
    "grant_type": 'client_credentials'
}

r = client.post(OAUTH_TOKEN_URL, data=payload)
if r.status_code != requests.codes.ok:
    raise ValueError(r.text)

access_token = r.json()['access_token']
headers = {'Authorization': 'Bearer {}'.format(access_token)}
result = client.get(version_url + '?application={}'.format(application), headers=headers)
if result.status_code != 200:
    raise Exception('Not able to access version end point')

version_records = result.json()
data = dict(
    application=application,
    version=version
)

if len(version_records) > 0:
    ver_id = version_records[0]['id']
    data['id'] = ver_id
    client_call = client.put
    url = version_url + '{}/'.format(ver_id)
else:
    client_call = client.post
    url = version_url

resp = client_call(url, headers=headers, data=data)
if resp.status_code not in (200, 201,):
    raise Exception('[{}] {}'.format(resp.status_code, resp.text))
print('Application {} updated to version {}'.format(application, version))
