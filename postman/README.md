# Postman Assets

This folder contains a collection and environment template to generate Auvious customer and agent room URLs via Postman.

## Files
- `Auvious-Rooms.postman_collection.json` — calls OAuth, creates a conference, and creates a ticket (plus a Genesys one-call flow).
- `Auvious-generic.postman_environment.json` — placeholders for `base_url`, `client_id`, `client_secret`, `application_id`, and output variables (`customer_url`, `agent_url`, etc.). Secrets are not committed.

## How to Use
1) In Postman, click **Import → Files** and select both JSON files from this folder.
2) Choose the imported environment `Auvious (generic)` and fill these variables:
   - `base_url` (e.g., `https://auvious.video`)
   - `client_id` / `client_secret` (your client credentials)
   - `application_id` (e.g., your Auvious app ID)
3) The collection uses Bearer auth at the collection level with `{{access_token}}`. Run requests in order:
   - **Auth: Get Access Token** (stores `access_token`)
   - **RTC: Create Conference** (stores `conference_id` and `agent_url`), mirrors the UI payload with `mode`, `metadata.participant_limit`, and generated `conferenceId`/`interactionId`. The script captures either `id` or `conferenceId` from the response to populate `conference_id`. If you need `creatorEndpoint`, register an endpoint via `/rtc-api/users/endpoints` and add that ID to the payload; otherwise it is omitted to avoid “user endpoint not found” errors.
   - **Security: Create Ticket (MULTI_USE_TICKET)** (stores `ticket_id`, `customer_url`, and `agent_url`) — pre-request script fails if `conference_id` is missing to enforce binding; ticket properties use snake_case (`conference_id`, `customer_id`) per API expectation.
   - Optional: **Genesys: Create Room** for the one-call flow returning both URLs.
4) After the ticket call, read the environment variables `customer_url` and `agent_url` for ready-to-use links.

## Hosted URLs (what to share)
- Customer: `https://<base_url>/t/<ticket_id>`
- Agent: `https://<base_url>/a?aid=<application_id>&roomId=<conference_id>`
- The collection sets `customer_url` and `agent_url` in the environment after the ticket request; copy them directly for distribution.

## Which flow to use (and in what order)
- Standard flow (separate steps, same conference): Auth → Create Conference → Create Ticket. The ticket is explicitly bound to the `conference_id` from the create call.
- Genesys facade (one-call flow): Auth → Genesys: Create Room. This creates its own conference and ticket internally and returns both URLs. Do not call `Create Conference` before it; the facade does its own conference creation and is independent of any prior `conference_id`.
- If you need extra customer tickets for a Genesys-created room, call `security/ticket` with the `conference_id` from the Genesys response; otherwise, keep flows separate.

## Notes
- Keep credentials in your Postman environment only; do not commit secrets.
- The collection expects client credentials with at least Agent role; Supervisor is required for recording/export scripts outside this flow.
