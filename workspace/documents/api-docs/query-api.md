# Query API

## Query Endpoint

The primary data retrieval endpoint is `POST /api/v1/query`. All queries are submitted as JSON in the request body.

```bash
curl -X POST https://api.datastack.io/api/v1/query \
  -H "Authorization: Bearer ds_live_abc123" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM events WHERE timestamp > now() - interval 1 hour"}'
```

The endpoint accepts SQL-like syntax with DataStack extensions for time-series operations. Results are returned as JSON arrays with column metadata.

Response times depend on query complexity and data volume. Simple aggregations typically return in under 200ms. Full table scans on large datasets may take up to 30 seconds.

## Query Syntax

DataStack supports a SQL-like query language with these extensions:

- **Time functions**: `now()`, `interval`, `bucket(timestamp, '5m')` for time-series grouping.
- **Approximate aggregations**: `approx_count_distinct()`, `approx_percentile()` for faster results on large datasets.
- **Window functions**: Standard SQL window functions (`ROW_NUMBER`, `LAG`, `LEAD`) are fully supported.
- **JSON access**: Use `->` and `->>` operators to query nested JSON columns.

Queries are validated before execution. Syntax errors return a `400` response with a detailed error message pointing to the offending token.

## Response Format

All query responses follow this structure:

```json
{
  "status": "ok",
  "data": [
    {"column1": "value1", "column2": 42},
    {"column1": "value2", "column2": 17}
  ],
  "metadata": {
    "row_count": 2,
    "execution_time_ms": 145,
    "bytes_scanned": 1048576
  }
}
```

Failed queries return `{"status": "error", "message": "..."}` with an appropriate HTTP status code. Partial results are never returned — queries either succeed completely or fail.
