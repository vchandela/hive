# Query FAQ

## Query Billing

DataStack query pricing is based on the amount of data scanned by each query, not the number of rows returned. Understanding query billing helps you optimize costs.

**How query billing works:**

- Each query scans a certain number of bytes from your tables.
- You are charged per TB of data scanned by your queries.
- Free plan: 10GB of query scanning per month included.
- Pro plan: 1TB of query scanning per month included. Additional query usage is billed at $5 per TB.

To see how much data a query scans, check the `bytes_scanned` field in the query response metadata. You can also view your total query usage in **Settings > Billing > Query Usage**.

**Tips to reduce query costs:**

- Add `WHERE` clauses to limit the data scanned per query.
- Select only the columns you need instead of using `SELECT *` in your queries.
- Use partitioned tables — queries on partitioned data only scan relevant partitions.

## Query Timeout

Queries that run longer than the configured timeout are automatically cancelled. Default query timeout settings:

| Plan | Query Timeout |
|------|--------------|
| Free | 30 seconds |
| Pro | 5 minutes |
| Enterprise | 30 minutes |

If your query times out:

1. **Simplify the query**: Break complex queries into smaller steps using temporary tables.
2. **Add filters**: Narrow the dataset with `WHERE` clauses so the query scans less data.
3. **Use approximate functions**: `approx_count_distinct()` is 10x faster than `count(distinct ...)` for large query result sets.

You can check query execution time in the query response metadata (`execution_time_ms`).

## Query Quota

Each plan has a monthly query quota:

- **Free**: 1,000 queries per month.
- **Pro**: 50,000 queries per month.
- **Enterprise**: Unlimited queries.

When you hit your query quota, subsequent queries return a `402 Payment Required` error with a message indicating your query limit has been reached. Upgrade your plan or wait until the next billing cycle.

Query counts reset on the first day of each month. Cached query results do not count against your quota.
