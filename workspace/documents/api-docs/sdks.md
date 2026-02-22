# SDKs

## Python SDK

The official Python SDK provides a high-level interface to the DataStack API.

```bash
pip install datastack-sdk
```

```python
from datastack import Client

client = Client(api_key="ds_live_abc123")
result = client.query("SELECT count(*) FROM events WHERE date = today()")
print(result.data)
```

The Python SDK handles authentication, retries, and response parsing automatically. It supports Python 3.8+ and has no required dependencies beyond `requests`.

Key features: automatic pagination for large result sets, connection pooling, and built-in rate limit handling with configurable backoff.

## Node.js SDK

The Node.js SDK is available via npm:

```bash
npm install @datastack/sdk
```

```javascript
const { DataStack } = require('@datastack/sdk');

const client = new DataStack({ apiKey: 'ds_live_abc123' });
const result = await client.query('SELECT count(*) FROM events');
console.log(result.data);
```

The SDK supports Node.js 16+ and uses `fetch` internally. It provides TypeScript type definitions out of the box.

## Authentication in SDKs

All SDKs accept an API key in the constructor. The key is sent as a `Bearer` token in the `Authorization` header on every request.

```python
# Python — key from environment variable
import os
client = Client(api_key=os.environ["DATASTACK_API_KEY"])
```

```javascript
// Node.js — key from environment variable
const client = new DataStack({ apiKey: process.env.DATASTACK_API_KEY });
```

Never hardcode API keys in source code. Use environment variables or a secrets manager. The SDKs will raise an error if no key is provided.
