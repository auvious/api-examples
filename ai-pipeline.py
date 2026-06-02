#!/usr/bin/env python

"""
Demonstrates the full Auvious AI pipeline for a recorded conversation:
  1. Create and download a video composition (MP4)
  2. Transcribe the conversation
  3. Translate the transcript
  4. Generate a summary
  5. Run sentiment analysis
  6. Run a custom analysis

Required env vars: AUVIOUS_URL, CLIENT_ID, CLIENT_SECRET, APPLICATION_ID, CONVERSATION_ID
Required roles: Supervisor (compositions, AI)
"""

import os
import time
import uuid
import requests

auvious_url = os.environ["AUVIOUS_URL"]
client_id = os.environ["CLIENT_ID"]
client_secret = os.environ["CLIENT_SECRET"]
application_id = os.environ["APPLICATION_ID"]
conversation_id = os.environ["CONVERSATION_ID"]

TRANSCRIPTION_LANGUAGE = "en"
TRANSLATION_LANGUAGE = "es"
CUSTOM_PROMPT = "Extract the top 3 key points from this conversation."

POLL_INTERVAL = 5  # seconds between state-check requests

BASE_HEADERS = {"User-Agent": "Auvious-AI-Demo 1.0"}


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_access_token():
    r = requests.post(
        f"{auvious_url}/security/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers=BASE_HEADERS,
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Auth failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


def json_headers(token):
    return {**BASE_HEADERS, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def bearer_headers(token):
    return {**BASE_HEADERS, "Authorization": f"Bearer {token}"}


# ── Composition ───────────────────────────────────────────────────────────────

def query_compositions(token):
    r = requests.get(
        f"{auvious_url}/composition/api/query/conversation/{conversation_id}",
        headers=bearer_headers(token),
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Query conversation failed: {r.status_code} {r.text}")
    compositions = r.json().get("compositions", [])
    video = next((c for c in compositions if c.get("type") == "VIDEO"), None)
    audio = next((c for c in compositions if c.get("type") == "AUDIO"), None)
    return video, audio


def create_composition(token, comp_type):
    body = {
        "name": f"export-{comp_type.lower()}-{uuid.uuid4()}",
        "conversationId": conversation_id,
        "type": comp_type.lower(),
        "audioFormat": "mp3",
        "videoFormat": "mp4",
        "layout": "GRID",
        "resolution": "320x240",
        "priority": "1",
    }
    r = requests.post(
            f"{auvious_url}/composition/api/request",
            json=body,
            headers=json_headers(token),
            timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Create {comp_type} composition failed: {r.status_code} {r.text}")
    cid = r.json()["id"]
    print(f"{comp_type} composition requested: {cid}")
    return cid


def ensure_compositions(token):
    """Return (video_id, audio_id); either may be None.

    VIDEO is never created — only reused if it already exists.
    AUDIO is created only when no composition of either type exists; otherwise
    an existing AUDIO composition is reused.
    """
    video_comp, audio_comp = query_compositions(token)
    nothing_existed = video_comp is None and audio_comp is None

    if video_comp:
        print(f"Reusing existing VIDEO composition: {video_comp['id']}")
        video_id = video_comp["id"]
        if video_comp.get("state") != "COMPLETED":
            wait_for_composition(token, video_id)
    else:
        print("No VIDEO composition found, skipping video download")
        video_id = None

    if audio_comp:
        print(f"Reusing existing AUDIO composition: {audio_comp['id']}")
        audio_id = audio_comp["id"]
        if audio_comp.get("state") != "COMPLETED":
            wait_for_composition(token, audio_id)
    elif nothing_existed:
        print("No compositions found, creating AUDIO-only composition")
        audio_id = create_composition(token, "AUDIO")
        wait_for_composition(token, audio_id)
    else:
        audio_id = None

    return video_id, audio_id


def wait_for_composition(token, composition_id):
    while True:
        r = requests.get(
            f"{auvious_url}/composition/api/query/conversation/{conversation_id}",
            headers=bearer_headers(token),
            timeout=10,
        )
        compositions = r.json().get("compositions", [])
        comp = next((c for c in compositions if c["id"] == composition_id), None)
        state = comp.get("state", "UNKNOWN") if comp else "UNKNOWN"
        if state in ("PREPROCESSING", "PROCESSING", "QUEUED"):
            print(f"  Composition: {state}, waiting...")
            time.sleep(POLL_INTERVAL)
        elif state == "COMPLETED":
            print("  Composition: COMPLETED")
            return
        else:
            raise RuntimeError(f"Composition ended with unexpected state: {state}")


def download_composition(token, composition_id, filename="export.mp4"):
    r = requests.get(
        f"{auvious_url}/composition/api/player/{conversation_id}/{composition_id}/url/attachment",
        headers={**bearer_headers(token), "Referer": auvious_url},
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Get signed URL failed: {r.status_code} {r.text}")

    signed_url = r.json()["url"]
    resp = requests.get(signed_url, stream=True, timeout=300)
    resp.raise_for_status()
    with open(filename, "wb") as f:
        f.write(resp.content)
    print(f"Downloaded to {filename}")


# ── AI helpers ────────────────────────────────────────────────────────────────

def ai_url(*parts):
    base = f"{auvious_url}/api/ai/{application_id}/conversations/{conversation_id}"
    return "/".join([base] + list(parts))


def wait_for_ai(token, url, label, response_key):
    """Poll a single-item AI resource URL until COMPLETED or FAILED.

    response_key is the top-level wrapper field in the JSON response
    (e.g. "transcription", "translation", "prompt").
    """
    while True:
        r = requests.get(url, headers=bearer_headers(token), timeout=10)
        if r.status_code != 200:
            raise RuntimeError(f"Poll {label} failed: {r.status_code} {r.text}")
        state = r.json()[response_key]["state"]
        if state == "COMPLETED":
            print(f"  {label}: COMPLETED")
            return
        if state == "FAILED":
            raise RuntimeError(f"{label} failed")
        print(f"  {label}: {state}, waiting...")
        time.sleep(POLL_INTERVAL)


def fetch_content(token, url, label):
    r = requests.get(url, headers=bearer_headers(token), timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"Fetch {label} content failed: {r.status_code} {r.text}")
    content = r.text
    preview = content[:500] + ("..." if len(content) > 500 else "")
    print(f"\n── {label} ──\n{preview}\n")
    return content


# ── AI operations ─────────────────────────────────────────────────────────────

def _resolve_ai(token, resource_id, poll_url, content_url, response_key, label):
    """Wait for resource if not completed, then fetch and print its content."""
    wait_for_ai(token, poll_url, label, response_key)
    fetch_content(token, content_url, label)
    return resource_id


def list_ai_resources(token, url, collection_key):
    """List AI resources at url, returning the items under collection_key.

    The AI list endpoints return 404 (not an empty array) when no resources
    exist yet for the conversation, so treat 404 as an empty list.
    """
    r = requests.get(url, headers=bearer_headers(token), timeout=10)
    if r.status_code == 404:
        return []
    if r.status_code != 200:
        raise RuntimeError(f"List {collection_key} failed: {r.status_code} {r.text}")
    return r.json().get(collection_key, [])


def ensure_transcription(token):
    """Reuse existing transcription for TRANSCRIPTION_LANGUAGE or create one."""
    transcriptions = list_ai_resources(token, ai_url("transcriptions"), "transcriptions")
    existing = next((t for t in transcriptions if t.get("language") == TRANSCRIPTION_LANGUAGE), None)

    if existing:
        print(f"Transcription already exists: {existing['id']} (state: {existing['state']})")
        tid = existing["id"]
    else:
        r2 = requests.post(
            ai_url("transcriptions"),
            json={"language": TRANSCRIPTION_LANGUAGE},
            headers=json_headers(token),
            timeout=10,
        )
        if r2.status_code != 200:
            raise RuntimeError(f"Create transcription failed: {r2.status_code} {r2.text}")
        tid = r2.json()["id"]
        print(f"Transcription requested: {tid}")

    return _resolve_ai(
        token, tid,
        ai_url("transcriptions", tid),
        ai_url("transcriptions", tid, "content"),
        "transcription", "Transcript",
    )


def ensure_translation(token, transcription_id):
    """Reuse existing translation for TRANSLATION_LANGUAGE or create one."""
    translations = list_ai_resources(
        token, ai_url("transcriptions", transcription_id, "translations"), "translations"
    )
    existing = next((t for t in translations if t.get("language") == TRANSLATION_LANGUAGE), None)

    if existing:
        print(f"Translation already exists: {existing['id']} (state: {existing['state']})")
        tid = existing["id"]
    else:
        r2 = requests.post(
            ai_url("transcriptions", transcription_id, "translations"),
            json={"language": TRANSLATION_LANGUAGE},
            headers=json_headers(token),
            timeout=10,
        )
        if r2.status_code != 200:
            raise RuntimeError(f"Create translation failed: {r2.status_code} {r2.text}")
        tid = r2.json()["id"]
        print(f"Translation requested: {tid}")

    return _resolve_ai(
        token, tid,
        ai_url("transcriptions", transcription_id, "translations", tid),
        ai_url("transcriptions", transcription_id, "translations", tid, "content"),
        "translation", f"Translation ({TRANSLATION_LANGUAGE})",
    )


def ensure_prompt(token, transcription_id, intent, label, custom_prompt=None):
    """Reuse existing prompt matching intent or create one."""
    prompts = list_ai_resources(
        token, ai_url("transcriptions", transcription_id, "prompts"), "prompts"
    )
    existing = next((p for p in prompts if p.get("intent") == intent), None)

    if existing:
        print(f"{label} already exists: {existing['id']} (state: {existing['state']})")
        pid = existing["id"]
    else:
        body = {"intent": intent}
        if custom_prompt:
            body["customPrompt"] = custom_prompt
        r2 = requests.post(
            ai_url("transcriptions", transcription_id, "prompts"),
            json=body,
            headers=json_headers(token),
            timeout=10,
        )
        if r2.status_code != 200:
            raise RuntimeError(f"Create {label} failed: {r2.status_code} {r2.text}")
        pid = r2.json()["id"]
        print(f"{label} requested: {pid}")

    return _resolve_ai(
        token, pid,
        ai_url("transcriptions", transcription_id, "prompts", pid),
        ai_url("transcriptions", transcription_id, "prompts", pid, "content"),
        "prompt", label,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    token = get_access_token()

    # 1. Compositions
    print("\n=== Compositions ===")
    video_id, audio_id = ensure_compositions(token)
    if video_id:
        download_composition(token, video_id, "export.mp4")
    if audio_id:
        download_composition(token, audio_id, "export.mp3")

    # 2. Transcription
    print("\n=== Transcription ===")
    transcription_id = ensure_transcription(token)

    # 3. Translation
    print("\n=== Translation ===")
    ensure_translation(token, transcription_id)

    # 4. Summary
    print("\n=== Summary ===")
    ensure_prompt(token, transcription_id, "summary", "Summary")

    # 5. Sentiment analysis
    print("\n=== Sentiment Analysis ===")
    ensure_prompt(token, transcription_id, "sentiment", "Sentiment")

    # 6. Custom analysis
    print("\n=== Custom Analysis ===")
    ensure_prompt(token, transcription_id, "prompt", "Custom analysis", custom_prompt=CUSTOM_PROMPT)


run()
