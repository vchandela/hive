# Getting Started

## Installation

Getting started with DataStack takes less than 5 minutes. You can use the web dashboard or connect via the API.

**Web Dashboard**: Sign up at app.datastack.io. No installation needed — everything runs in your browser. You get a free workspace with 1GB of storage and 20 API requests per minute.

**API / SDK**: Install the SDK for your language:

```bash
# Python
pip install datastack-sdk

# Node.js
npm install @datastack/sdk
```

Configure your API key (see Authentication docs for details) and you're ready to query.

## Your First Query

Once you have data in your workspace (via CSV import or API), run your first query:

```python
from datastack import Client

client = Client(api_key="ds_live_abc123")

result = client.query("""
    SELECT date, count(*) as events
    FROM my_events
    WHERE timestamp > now() - interval '7 days'
    GROUP BY date
    ORDER BY date
""")

for row in result.data:
    print(f"{row['date']}: {row['events']} events")
```

This fetches the daily event count for the last 7 days. DataStack's query language is SQL-like with time-series extensions.

## Next Steps

Now that you're connected, explore these guides:

- **Building Dashboards** — Create visual reports from your data.
- **Custom Queries** — Learn the full query syntax with advanced filters.
- **Setting Up Alerts** — Get notified when metrics cross thresholds.
- **Data Import** — Load data from CSV files or external APIs.
