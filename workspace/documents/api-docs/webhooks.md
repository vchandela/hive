# Webhooks

## Webhook Setup

DataStack can send real-time notifications to your application via webhooks. To configure a webhook:

1. Go to **Settings > Webhooks** in the dashboard.
2. Click **Add Endpoint**.
3. Enter your HTTPS endpoint URL.
4. Select the event types you want to receive.
5. Click **Save**.

DataStack will send a verification `POST` request to your endpoint with a challenge token. Your endpoint must respond with the token to confirm ownership.

All webhook payloads are signed with HMAC-SHA256. The signature is included in the `X-DataStack-Signature` header. Always verify signatures before processing webhook data.

## Event Types

Available webhook event types:

| Event | Description |
|-------|-------------|
| `query.completed` | A scheduled query finished executing |
| `alert.triggered` | An alert rule condition was met |
| `import.completed` | A data import job finished |
| `import.failed` | A data import job failed |
| `dashboard.shared` | A dashboard was shared with new users |

Each event payload includes a `type` field, a `timestamp`, and a `data` object with event-specific details.

## Retry Policy

If your endpoint returns a non-2xx status code, DataStack retries the delivery with exponential backoff:

- Retry 1: after 1 minute
- Retry 2: after 5 minutes
- Retry 3: after 30 minutes
- Retry 4: after 2 hours
- Retry 5: after 12 hours (final attempt)

After 5 failed attempts, the event is marked as undeliverable and your webhook endpoint is flagged as unhealthy. You will receive an email notification when this happens. Resolve the issue and re-enable the endpoint from the dashboard.
