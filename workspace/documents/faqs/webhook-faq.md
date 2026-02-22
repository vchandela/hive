# Webhook FAQ

## Webhook Failures

Webhook deliveries can fail for several reasons. Here's how to diagnose and fix common webhook issues:

**Common webhook failure causes:**

- **Endpoint returned non-2xx status**: Your webhook server responded with an error. Check your server logs for the root cause.
- **Connection timeout**: DataStack couldn't connect to your webhook endpoint within 10 seconds. Ensure your server is reachable and responsive.
- **SSL certificate error**: Your webhook endpoint's SSL certificate is invalid or expired. Renew it and ensure the full certificate chain is configured.
- **DNS resolution failed**: The webhook endpoint domain couldn't be resolved. Check your DNS configuration.

You can view webhook delivery logs in **Settings > Webhooks > Delivery History**. Each log entry shows the HTTP status code, response time, and response body for the webhook request.

## Debugging Webhooks

To debug webhook issues:

1. **Use the test feature**: Click **Send Test Event** on your webhook configuration page. This sends a sample webhook payload to your endpoint.
2. **Check delivery logs**: Review the last 30 days of webhook deliveries. Failed webhook attempts are highlighted in red.
3. **Use a webhook testing tool**: Services like webhook.site or RequestBin let you inspect incoming webhook payloads without writing code.
4. **Verify the signature**: Ensure your webhook handler correctly validates the `X-DataStack-Signature` header. An incorrect webhook signature verification will cause your handler to reject valid webhook events.

## Webhook Alternatives

If webhooks don't fit your architecture, consider these alternatives:

- **Polling**: Query the `/api/v1/events` endpoint at regular intervals. Less efficient than webhooks but simpler to implement.
- **WebSocket**: Connect to the real-time events stream at `wss://stream.datastack.io`. Lower latency than webhooks, but requires maintaining a persistent connection.
- **Email notifications**: For non-programmatic use cases, configure email alerts instead of webhooks. Available in **Settings > Notifications**.
