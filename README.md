# Auvious API Examples
A few examples demonstrating how to use the Auvious API to create a normal or a scheduled video call.

## Postman Collections
- See `postman/` for separate, ready-to-import collections and a shared environment template. Import the JSON files in Postman, fill in `base_url`, `client_id`, `client_secret`, and `application_id`, then choose the flow:
  - Rooms collection: Auth → Create Conference → Create Ticket (or the one-call flow). Environment stores `customer_url` and `agent_url`.
  - Recording collection: Auth → Start Recording → Stop Recording → Recording: Get → Recording: Get State. Requires `conference_id`; if `interaction_id` is blank, it uses `conference_id` as the conversationId (no random GUIDs). Start stores `recorder_id`, `recorder_instance_id`, and `conversation_id` for subsequent calls. Environment stores recorder metadata and state. The conference payload omits `creatorEndpoint`; if you need it, register an endpoint first (`/rtc-api/users/endpoints`) and add its ID to the payload.
  - Compositions collection: Auth → Request Video → Query Conversation → Get Signed URL → Delete. Requires `conversation_id` from a recorded call (after recording is stopped/uploaded); stores `composition_id` and `composition_signed_url`. Compositions are asynchronous—poll query/state before proceeding; delete requires Supervisor role and an allowed state.
- Postman coverage is scoped to core/basic flows (rooms, recording start/stop/status, compositions) to give Postman users a clear initial path for basic conferencing use cases.
