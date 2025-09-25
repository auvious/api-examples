#!/usr/bin/env python

from http.client import HTTPException
import os
import uuid
import time
import requests

# base url
auvious_url = os.environ["AUVIOUS_URL"]
client_id = os.environ["CLIENT_ID"]  # needs Supervisor role to run
client_secret = os.environ["CLIENT_SECRET"]
conversation_id = os.environ["CONVERSATION_ID"]

# Define base headers with the User-Agent
BASE_HEADERS = {
    "User-Agent": "Testing 1.0"
}


def get_access_token():
    """Get access token."""
    url = f"{auvious_url}/security/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    headers = BASE_HEADERS.copy()

    r = requests.post(
        url,
        headers=headers,
        data=payload,
        timeout=5,
    )

    if r.status_code != 200:
        raise HTTPException(
            f"Failed to get access token: status = {r.status_code}, body = {r.text}"
        )

    return r.json()["access_token"]

def check_recording(access_token):
    """Check if the conversation is recorded."""
    headers = BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {access_token}"

    r = requests.get(
        f"{auvious_url}/composition/api/query/conversation/{conversation_id}",
        headers=headers,
        timeout=5,
    )

    if r.status_code != 200:
        raise HTTPException(f"Failed to get conversation: status {r.status_code}, body = {r.text}")


def delete_mp4_if_exists(access_token):
    """Delete video composition if exists."""
    headers = BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {access_token}"

    r = requests.get(
        f"{auvious_url}/composition/api/query/conversation/{conversation_id}",
        headers=headers,
        timeout=5,
    )

    response = r.json()

    compositions = response.get("compositions", [])

    video_composition = next(
        (comp for comp in compositions if comp.get("type") == "VIDEO"), None
    )

    if video_composition:
        # Found a video composition
        composition_id = video_composition.get("id")
        print(f"Found video composition with id: {composition_id}")
        # delete composition to create a new one
        r = requests.delete(
            f"{auvious_url}/composition/api/{conversation_id}/{composition_id}/delete",
            headers=headers,
            timeout=5,
        )
        if r.status_code == 204:
            print(f"Composition with id {composition_id} deleted")
    else:
        print("No video composition found in the response")


def create_video_composition(access_token):
    """Creates video composition."""
    headers = BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {access_token}"
    headers["Content-Type"] = "application/json"

    r = requests.post(
        f"{auvious_url}/composition/api/request",
        json={
            "name": f"export-{str(uuid.uuid4())}",
            "conversationId": conversation_id,
            "audioFormat": "mp3",
            "videoFormat": "mp4",
            "type": "video",
            "resolution": "320x240",
            "layout": "GRID",
            "priority": "1",
        },
        headers=headers,
        timeout=5,
    )

    if r.status_code != 200:
        raise HTTPException(
            f"Failed to create video composition: status = {r.status_code}, body = {r.text}"
        )

    return r.json()["id"]


def wait_for_completion(access_token, composition_id):
    """Wait for composition to be completed."""
    headers = BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {access_token}"

    r = requests.get(
        f"{auvious_url}/composition/api/query/conversation/{conversation_id}",
        headers=headers,
        timeout=5,
    )

    if r.status_code == 404:
        raise HTTPException(f"Conversation {conversation_id} not found")

    response = r.json()
    compositions = response.get("compositions", [])

    video_composition = next(
        (comp for comp in compositions if comp.get("id") == composition_id), None
    )

    video_composition_state = video_composition.get("state")

    if video_composition_state in ["PREPROCESSING", "PROCESSING", "QUEUED"]:
        print("Composition is still processing, waiting 5 seconds")
        time.sleep(5)
        return wait_for_completion(access_token, composition_id)
    else:
        print(f"Composition state: {video_composition_state}")
        if video_composition_state != "COMPLETED":
            raise HTTPException(f"Composition failed with state: {video_composition_state}")


def get_composition_signed_url(access_token, composition_id):
    """Get composition download(signed) url."""
    headers = BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {access_token}"
    headers["Referer"] = auvious_url

    r = requests.get(
        f"{auvious_url}/composition/api/player/{conversation_id}/{composition_id}/url/attachment",
        headers=headers,
        timeout=5,
    )

    if r.status_code != 200:
        raise HTTPException(
            f"Failed to get composition signed url: status = {r.status_code}, body = {r.text}"
        )

    return r.json()["url"]


def download_file(url, file_name):
    """Download a file from the given URL and save it to the specified file path."""
    try:
        # Send a GET request to the URL
        response = requests.get(url, stream=True, timeout=555)
        response.raise_for_status()  # Check if the download was successful

        # Open the file in binary write mode and save the content
        with open(file_name, "wb") as file:
            file.write(response.content)
        print(f"Downloaded '{file_name}' from '{url}'")
    except requests.RequestException as e:
        print(f"Error downloading the file: {e}")


def run():
    """Run the script."""
    access_token = get_access_token()

    check_recording(access_token)

    delete_mp4_if_exists(access_token)

    composition_id = create_video_composition(access_token)

    print(f"Created composition with id: {composition_id}")

    wait_for_completion(access_token, composition_id)

    signed_url = get_composition_signed_url(access_token, composition_id)

    download_file(signed_url, "export.mp4")


run()
