# Auvious API Examples
A few examples demonstrating how to use the Auvious API to create a normal or a scheduled video call.

## Postman Collections
- See `postman/` for separate, ready-to-import collections and a shared environment template. Import the JSON files in Postman, fill in `base_url`, `client_id`, `client_secret`, and `application_id`, then choose the flow:
  - Rooms collection: Auth → Create Conference → Create Ticket (or the one-call Genesys flow). Environment stores `customer_url` and `agent_url`.
  - Recording collection: Auth → (optional) Create Conference → Register Endpoint → Join Conference → Start Recording → (optional) Set RECORDER metadata → Leave. Environment stores recorder metadata. The conference payload omits `creatorEndpoint`; if you need it, register an endpoint first (`/rtc-api/users/endpoints`) and add its ID to the payload.
