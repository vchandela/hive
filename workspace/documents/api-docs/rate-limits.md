# Rate Limits

## Rate Limit Policy

DataStack enforces rate limits to ensure fair usage and platform stability. The default limits are:

| Plan | Requests per minute | Concurrent queries |
|------|--------------------|--------------------|
| Free | 20 | 2 |
| Pro | 100 | 10 |
| Enterprise | 1000 | 50 |

Rate limits are applied per API key. If you have multiple keys, each has its own independent limit.

Requests that exceed the limit receive a `429 Too Many Requests` response. The response includes headers indicating when you can retry.

## Headers

Every API response includes rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 73
X-RateLimit-Reset: 1700000060
```

- `X-RateLimit-Limit`: Your maximum requests per minute.
- `X-RateLimit-Remaining`: Requests remaining in the current window.
- `X-RateLimit-Reset`: Unix timestamp when the window resets.

When you receive a `429` response, wait until the `X-RateLimit-Reset` time before retrying. Alternatively, use the `Retry-After` header which gives the wait time in seconds.

## Handling 429s

Best practices for handling rate limits:

1. **Implement exponential backoff**: Start with a 1-second delay and double it on each `429`, up to a maximum of 60 seconds.
2. **Use the `Retry-After` header**: Respect the server's suggested wait time.
3. **Queue requests**: Buffer outgoing requests and process them at a steady rate below your limit.
4. **Monitor usage**: Track `X-RateLimit-Remaining` to proactively throttle before hitting the limit.

For burst workloads, consider upgrading to a higher plan or contacting sales for custom limits.
