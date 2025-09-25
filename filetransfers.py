#!/usr/bin/env python

from http.client import HTTPException
import os
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

def get_files(access_token):
    """Get files from the conversation."""
    headers = BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {access_token}"

    r = requests.get(
        f"{auvious_url}/rtc-api/filetransfers",
        headers=headers,
        timeout=5,
        params={"interactionId": conversation_id},
    )

    if r.status_code != 200:
        raise HTTPException(f"Failed to get files: status {r.status_code}, body = {r.text}")

    return r.json()


def get_filetransfer_signed_url(access_token, file_transfer_id):
    """Get file transfer download(signed) url."""
    headers = BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {access_token}"
    headers["Referer"] = auvious_url

    r = requests.post(
        f"{auvious_url}/rtc-api/filetransfers/{file_transfer_id}/signedUrl",
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

    files = get_files(access_token)

    print(f"number of Files: {len(files)}")

    for file in files:
        file_transfer_id = file.get("fileTransferId")
        original_filename = file.get("filename")
        file_name = f"{file_transfer_id}_{original_filename}"
        if file_transfer_id:
            signed_url = get_filetransfer_signed_url(access_token, file_transfer_id)
            print(f"Downloading file: {file_name} from URL: {signed_url}")
            download_file(signed_url, file_name)
        else:
            print("No fileTransferId found for this file, skipping download, but this is unexpected.")

run()
