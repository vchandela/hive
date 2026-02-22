# Authentication

## Auth Tokens

DataStack uses bearer tokens for API authentication. Every request to the API must include an `Authorization` header with a valid token.

To authenticate, include the header in your request:

```
Authorization: Bearer ds_live_abc123xyz789
```

Tokens are issued when you create an API key in the DataStack dashboard. Each token is scoped to a single workspace and inherits the permissions of the user who created it.

Tokens do not expire automatically, but they can be revoked at any time from the API Keys page. We recommend rotating tokens every 90 days as a security best practice.

## API Key Generation

To generate a new API key:

1. Navigate to **Settings > API Keys** in the DataStack dashboard.
2. Click **Create New Key**.
3. Select the permission scope: `read`, `write`, or `admin`.
4. Copy the generated token immediately — it will not be shown again.

Each workspace can have up to 50 active API keys. Keys with `admin` scope can create and delete other keys.

The API key format is `ds_{environment}_{random}` where environment is `live` or `test`. Test keys can only access sandbox data.

## Token Refresh

DataStack API tokens are long-lived and do not require refresh flows. If you need to rotate a token:

1. Generate a new key (see above).
2. Update your application to use the new key.
3. Revoke the old key from the dashboard.

There is no OAuth refresh token mechanism — DataStack uses static bearer tokens for simplicity. For short-lived access, use the `/api/v1/auth/temporary-token` endpoint, which issues a token valid for 1 hour.
