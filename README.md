# Auvious API Examples
A few examples demonstrating how to use the Auvious API to create a normal or a scheduled video call.

## Postman Collection
- See `postman/` for a ready-to-import collection and environment template to create customer/agent room URLs. Import both JSON files in Postman, fill in your `base_url`, `client_id`, `client_secret`, and `application_id`, then run the requests in order (Auth → Create Conference → Create Ticket). The environment will store the resulting `customer_url` and `agent_url`. The conference payload omits `creatorEndpoint`; if you need it, register an endpoint first (`/rtc-api/users/endpoints`) and add its ID to the payload.
