#!/usr/bin/env python
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import os
import uuid
import requests


# base url
auvious_url = os.environ["AUVIOUS_URL"]
client_id = os.environ[
    "CLIENT_ID"
]  # Client needs Agent role in order for several requests to work
client_secret = os.environ["CLIENT_SECRET"]
application_id = os.environ["APPLICATION_ID"]

r = requests.post(
    f"{auvious_url}/security/oauth/token",
    params={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    },
    timeout=5,
)

access_token = r.json()["access_token"]
# print(access_token)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}",
}

customer_id = str(uuid.uuid4())
interaction_id = str(uuid.uuid4())

r = requests.post(
    f"{auvious_url}/security/genesys/room",
    json={
        "applicationId": application_id,
        "cdestination": "standalone",
        "customerId": customer_id,
        "interactionId": interaction_id,
        "ticketExpirationSeconds": 14400,
        "urlBase": auvious_url,
    },
    headers=headers,
    timeout=5,
)

if r.status_code != 200:
    raise RuntimeError(f"Failed to create room: {r.text}")

ticket_url = r.json()["ticketUrl"]
agent_url = r.json()["agentUrl"]

print(f"Customer url: {ticket_url}")
print(f"Agent url: {agent_url}")

# Get the roomId query param from agent_url
parsed_agent_url = urlparse(agent_url)
agent_url_query_params = parse_qs(parsed_agent_url.query)

# Get a specific parameter, e.g., 'name'
room_id = agent_url_query_params.get("roomId", [None])[0]
cdestination = agent_url_query_params.get("cdestination", [None])[0]
corigin = agent_url_query_params.get("corigin", [None])[0]

print(f"Room ID: {room_id}")
print(f"Call Destination: {cdestination}")
print(f"Call Origin: {corigin}")

# Start recording
r = requests.post(
    f"{auvious_url}/rtc-recorder/api/recordings/start",
    json={
        "applicationId": application_id,
        "conferenceId": room_id,
        "conversationId": interaction_id,
        "audio": True,
        "video": True,
    },
    headers=headers,
    timeout=5,
)

if r.status_code != 200:
    raise RuntimeError(f"Failed to start recording: {r.text}")

recorder_id = r.json()["recorderId"]
recorder_instance_id = r.json()["instanceId"]

# Create a new interaction with the recording metadata
r = requests.post(
    f"{auvious_url}/rtc-api/interactions",
    json={
        "interactionId": interaction_id,
        "type": "video",
        "data": {
            "callStartAt": datetime.utcnow().isoformat() + "Z",
            "callDestination": cdestination,
            "callOrigin": corigin,
            "callOriginMode": "website",
            "customerId": customer_id,
            "customerMetadata": {},
            "integrationInteractionAvailable": False,
            "roomName": room_id,
            "recorderId": recorder_id,
            "recorderInstanceId": recorder_instance_id,
        },
    },
    headers=headers,
    timeout=5,
)

if r.status_code != 200:
    raise RuntimeError(f"Failed to create interaction entity: {r.text}")

# register and join the room so we can do the next request
r = requests.post(
    f"{auvious_url}/rtc-api/users/endpoints",
    json={"keepAliveSeconds": 5},
    headers=headers,
    timeout=5,
)

if r.status_code != 200:
    raise RuntimeError(f"Failed to register endpoint: {r.text}")

user_endpoint_id = r.json()
print(f"User endpoint ID: {user_endpoint_id}")

# join the room
r = requests.post(
    f"{auvious_url}/rtc-api/conferences/join",
    json={"conferenceId": room_id, "userEndpointId": user_endpoint_id},
    headers=headers,
    timeout=5,
)

if r.status_code != 200:
    raise RuntimeError(f"Failed to join room: {r.text}")

# set recording metadata on conference
r = requests.post(
    f"{auvious_url}/rtc-api/conferences/updateMetadata",
    json={
        "conferenceId": room_id,
        "operation": "SET",
        "key": "RECORDER",
        "value": '{"on":true}',
        "userEndpointId": user_endpoint_id,
    },
    headers=headers,
    timeout=5,
)

if r.status_code != 204:
    raise RuntimeError(f"Failed to set recording metadata: {r.text}")

# finally leave the room
r = requests.post(
    f"{auvious_url}/rtc-api/conferences/leave",
    json={
        "conferenceId": room_id,
        "userEndpointId": user_endpoint_id,
        "reason": "my purpose is complete now",
    },
    headers=headers,
    timeout=5,
)

if r.status_code != 204:
    raise RuntimeError(f"Failed to leave room: {r.text}")
