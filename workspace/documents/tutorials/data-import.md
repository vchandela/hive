# Data Import

## CSV Import

The fastest way to get data into DataStack is via CSV upload:

1. Go to **Data > Import** in the dashboard.
2. Click **Upload CSV**.
3. Select your file (max 500MB per upload).
4. DataStack auto-detects column types (string, number, date, boolean).
5. Review the schema and adjust column types if needed.
6. Click **Import**.

Import progress is shown in real time. Small files (under 10MB) typically complete in under 10 seconds.

CSV requirements:
- UTF-8 encoding
- Comma-separated (configurable delimiter)
- First row must be column headers
- No duplicate column names

## API Import

For programmatic data loading, use the Import API:

```bash
curl -X POST https://api.datastack.io/api/v1/import \
  -H "Authorization: Bearer ds_live_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "table": "my_events",
    "data": [
      {"event": "signup", "user_id": 1, "timestamp": "2024-01-15T10:30:00Z"},
      {"event": "purchase", "user_id": 1, "timestamp": "2024-01-15T11:00:00Z"}
    ]
  }'
```

The API accepts up to 10,000 rows per request. For larger loads, use batching or the bulk import endpoint (`/api/v1/import/bulk`) which accepts newline-delimited JSON.

## Scheduling Imports

Automate recurring imports with scheduled jobs:

1. Go to **Data > Scheduled Imports**.
2. Click **New Schedule**.
3. Configure the source: URL (fetches CSV/JSON from an HTTP endpoint), S3 bucket, or Google Cloud Storage.
4. Set the schedule: hourly, daily, or weekly.
5. Map the source columns to your DataStack table.

Scheduled imports run automatically and notify you on failure. Each run is logged with row counts and error details.
