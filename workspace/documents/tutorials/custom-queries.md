# Custom Queries

## Query Builder

The DataStack Query Builder provides a visual interface for constructing queries without writing SQL. Access it from any dashboard widget or from the **Explore** page.

The builder has four sections:

1. **Source**: Select the table or data source.
2. **Columns**: Choose which columns to include.
3. **Filters**: Add conditions (e.g., `status = 'active'`, `created_at > 2024-01-01`).
4. **Group By**: Aggregate results by one or more columns.

The builder generates SQL in real time. You can switch to the SQL editor at any point to refine the query manually. Changes in the SQL editor are reflected back in the builder when possible.

## Advanced Filters

Filters support these operators:

| Operator | Example | Description |
|----------|---------|-------------|
| `=` / `!=` | `status = 'active'` | Exact match |
| `>` / `<` / `>=` / `<=` | `amount > 100` | Numeric comparison |
| `LIKE` | `name LIKE '%test%'` | Pattern matching |
| `IN` | `region IN ('us', 'eu')` | Set membership |
| `BETWEEN` | `date BETWEEN '2024-01-01' AND '2024-06-30'` | Range |
| `IS NULL` / `IS NOT NULL` | `email IS NOT NULL` | Null checks |

Filters can be combined with `AND` and `OR`. Use parentheses for complex conditions:

```sql
WHERE (status = 'active' AND plan = 'pro') OR (created_at > '2024-06-01')
```

## Saving Queries

Save frequently used queries for reuse:

1. Write or build your query.
2. Click **Save Query**.
3. Give it a name and optional description.
4. Choose visibility: **Private** (only you) or **Workspace** (all members).

Saved queries appear in the **Queries** library. They can be used as widget data sources, referenced in alerts, or shared with teammates.
