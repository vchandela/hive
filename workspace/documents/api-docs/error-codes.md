# Error Codes

## Client Errors (4xx)

Client errors indicate a problem with the request. Common codes:

| Code | Name | Description |
|------|------|-------------|
| 400 | Bad Request | The request body is malformed or missing required fields. Check the `message` field for details. |
| 401 | Unauthorized | The API key is missing, invalid, or revoked. Generate a new key from the dashboard. |
| 403 | Forbidden | The API key does not have permission for this operation. Check the key's scope (read/write/admin). |
| 404 | Not Found | The requested resource does not exist. Verify the endpoint URL and resource ID. |
| 422 | Unprocessable Entity | The request is well-formed but contains invalid values. For queries, this usually means a SQL syntax error. |
| 429 | Too Many Requests | Rate limit exceeded. See the Rate Limits documentation for handling strategies. |

## Server Errors (5xx)

Server errors indicate a problem on DataStack's side. These are rare but can occur during maintenance or outages.

| Code | Name | Description |
|------|------|-------------|
| 500 | Internal Server Error | An unexpected error occurred. Retry the request after a short delay. If persistent, contact support. |
| 502 | Bad Gateway | A backend service is temporarily unavailable. Retry after 5-10 seconds. |
| 503 | Service Unavailable | DataStack is undergoing maintenance. Check the status page at status.datastack.io. |

For all 5xx errors, implement retry logic with exponential backoff. The platform self-heals within minutes in most cases.

## Error Response Format

All error responses follow this structure:

```json
{
  "status": "error",
  "code": 422,
  "message": "SQL syntax error at position 15: unexpected token 'FORM' (did you mean 'FROM'?)",
  "request_id": "req_abc123xyz"
}
```

Include the `request_id` when contacting support — it helps us trace the exact request in our logs.
