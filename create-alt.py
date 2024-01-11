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
    },
    timeout=5
)

access_token = r.json()['access_token']
# print(access_token)

headers = {
  'Content-Type': 'application/json',
  'Authorization': f'Bearer {access_token}'
}

r = requests.post(
  f"{auvious_url}/security/genesys/room",
  json={
      'applicationId': application_id,
      'cdestination': 'standalone',
      'customerId': str(uuid.uuid4()),
      'interactionId': str(uuid.uuid4()),
      'ticketExpirationSeconds': 14400,
      'urlBase': auvious_url
  },
  headers = headers,
  timeout=5
)

print(f"Customer url: {r.json()['ticketUrl']}")
print(f"Agent url: {r.json()['agentUrl']}")
