#!/usr/bin/env python

import os
import uuid
import requests

# base url
auvious_url = os.environ['AUVIOUS_URL']
client_id = os.environ['CLIENT_ID']
client_secret = os.environ['CLIENT_SECRET']
application_id = os.environ['APPLICATION_ID']

r = requests.post(
    f"{auvious_url}/security/oauth/token",
    params={
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
)

access_token = r.json()['access_token']
# print(access_token)

headers = {
  'Content-Type': 'application/json',
  'Authorization': f'Bearer {access_token}'
}

r = requests.post(
  f"{auvious_url}/rtc-api/conferences/create",
  json={},
  headers = headers
)

conference_id = r.json()['id']

r = requests.post(
  f'{auvious_url}/security/ticket',
  json={
      'type': 'MULTI_USE_TICKET',
      'ttl': 14400,
      'length': 6,
      'properties': {
          'applicationId': application_id,
          'conference_id': conference_id,
          'customer_id': str(uuid.uuid4())
      }

          },
  headers = headers)

ticket = r.json()['id']

print(f"Customer url: {auvious_url}/t/{ticket}")
print(f"Agent url: {auvious_url}/a?aid={application_id}&roomId={conference_id}")