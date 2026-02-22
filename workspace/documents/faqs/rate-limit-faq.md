# Rate Limit FAQ

## Why Am I Rate Limited?

If you're seeing `429 Too Many Requests` errors, your application is exceeding the rate limit for your plan. Here are common rate limit scenarios:

**Batch operations**: If you're running many API requests in a loop, you'll hit the rate limit quickly. Instead of individual requests, use the batch endpoints — for example, `/api/v1/import/bulk` for data loading handles thousands of rows in a single rate-limited request.

**Multiple applications**: If several applications share the same API key, their combined rate limit usage counts against a single quota. Create separate API keys for each application so you can track rate limit usage independently.

**Dashboard auto-refresh**: If you have many dashboards set to auto-refresh, each refresh triggers API queries that count against your rate limit. Increase refresh intervals for non-critical dashboards to reduce rate limit pressure.

## Upgrading Plans

If you're consistently hitting rate limits, consider upgrading to a higher plan:

| Plan | Rate Limit | Price |
|------|-----------|-------|
| Free | 20 req/min | $0/month |
| Pro | 100 req/min | $49/month |
| Enterprise | 1000 req/min | Custom rate |

To upgrade your rate limit tier:

1. Go to **Settings > Billing**.
2. Click **Upgrade Plan**.
3. Select the plan with the rate limit that fits your usage.
4. Enter payment details and confirm.

Rate limit changes take effect immediately upon upgrade. There's no downtime and no need to rotate your API keys when changing your rate limit tier.

## Enterprise Limits

Enterprise customers can request custom rate limits tailored to their workload:

- **Burst allowance**: Temporary rate limit increases (up to 5x your base limit) for up to 60 seconds.
- **Dedicated capacity**: Isolated rate limit pools that don't share resources with other customers.
- **Per-endpoint limits**: Different rate limits for different API endpoints based on your usage patterns.

Contact your account manager or email enterprise@datastack.io to discuss custom rate limit configurations.
