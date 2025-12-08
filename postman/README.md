# Postman Assets

This folder contains a collection and environment template to generate Auvious customer and agent room URLs via Postman.

## Files
- `Auvious-Rooms.postman_collection.json` — room creation flows: OAuth, create conference, create ticket, plus a Genesys one-call flow.
- `Auvious-Recording.postman_collection.json` — recording flow: OAuth + start/stop recording for an existing conference.
- `Auvious-Compositions.postman_collection.json` — composition flow: OAuth + request video composition, query, and fetch signed URL.
- `Auvious-generic.postman_environment.json` — placeholders for `base_url`, `client_id`, `client_secret`, `application_id`, and output variables (`customer_url`, `agent_url`, etc.). Secrets are not committed.

## How to Use
1) In Postman, click **Import → Files** and select the JSON files from this folder (Rooms, Recording, and the environment).
2) Choose the imported environment `Auvious (generic)` and fill these variables:
   - `base_url` (e.g., `https://auvious.video`)
   - `client_id` / `client_secret` (your client credentials)
   - `application_id` (e.g., your Auvious app ID)
3) Collections use Bearer auth at the collection level with `{{access_token}}`.
   - Rooms collection order: **Auth → Create Conference → Create Ticket**. Optional: **Genesys: Create Room** (one-call, independent of the standard flow).
   - Recording collection order: **Auth → Start Recording → Stop Recording → Recording: Get → Recording: Get State**. Requires `conference_id` (from Rooms or elsewhere) and `interaction_id` (auto-generated if blank). Start stores `recorder_id` and `recorder_instance_id` used by subsequent calls; state is stored as `recorder_state`.
   - Compositions collection order: **Auth → Composition: Request Video → Composition: Query Conversation → Composition: Get Signed URL**. Requires `conversation_id` (set from your call recording/interaction). Request stores `composition_id`; signed URL stored as `composition_signed_url`.
4) After the Rooms ticket call, read the environment variables `customer_url` and `agent_url` for ready-to-use links.

## Hosted URLs (what to share)
- Customer: `https://<base_url>/t/<ticket_id>`
- Agent: `https://<base_url>/a?aid=<application_id>&roomId=<conference_id>`
- The collection sets `customer_url` and `agent_url` in the environment after the ticket request; copy them directly for distribution.

## Which flow to use (and in what order)
- Rooms, standard: Auth → Create Conference → Create Ticket. The ticket is bound to that `conference_id`.
- Rooms, Genesys facade: Auth → Genesys: Create Room. This creates its own conference and ticket. Do not precede it with Create Conference; they are independent. If you need extra tickets for a Genesys-created room, call `security/ticket` with that `conference_id`.
- Recording: Use the Recording collection. Supply `conference_id` from the Rooms flow (or your own conference). Then Auth → Start Recording → Stop Recording → Recording: Get → Recording: Get State.
- Compositions: Use the Compositions collection. Supply `conversation_id` from the recorded call, then Auth → Request Video → Query → Get Signed URL.

## Recording flow (API-driven)
Recording collection sequence:
- Auth → Start Recording → Stop Recording → Recording: Get → Recording: Get State.
- Needs `application_id`, `conference_id`, and `interaction_id`. If `interaction_id` is empty, the collection generates one before starting recording. Start stores `recorder_id` and `recorder_instance_id` used by subsequent calls; state stored as `recorder_state`.

Compositions collection sequence:
- Auth → Composition: Request Video → Composition: Query Conversation → Composition: Get Signed URL.
- Needs `conversation_id`. Request stores `composition_id`; Query can refresh `composition_state`; Get Signed URL stores `composition_signed_url`.

## Notes
- Keep credentials in your Postman environment only; do not commit secrets.
- The collection expects client credentials with at least Agent role; Supervisor is required for recording/export scripts outside this flow.
