# Building Dashboards

## Dashboard Basics

Dashboards in DataStack are collections of charts, tables, and metrics arranged on a flexible grid. Each dashboard belongs to a workspace and can contain up to 50 widgets.

To create a dashboard:

1. Click **Dashboards** in the left sidebar.
2. Click **New Dashboard**.
3. Give it a name and optional description.
4. Start adding widgets.

Dashboards auto-refresh every 5 minutes by default. You can change the refresh interval in dashboard settings or set it to manual refresh only.

## Adding Charts

Each widget is powered by a query. To add a chart:

1. Click **Add Widget** on your dashboard.
2. Choose a chart type: line, bar, area, pie, table, or single metric.
3. Write a query or select a saved query.
4. Configure the visualization: axes, colors, labels, and formatting.
5. Click **Save**.

Example query for a time-series line chart:

```sql
SELECT bucket(timestamp, '1h') as hour, count(*) as requests
FROM api_logs
WHERE timestamp > now() - interval '24 hours'
GROUP BY hour
ORDER BY hour
```

DataStack automatically detects time columns and uses them for the X axis. Numeric columns become Y axis values.

## Sharing

Dashboards can be shared with specific users or made public:

- **Workspace members**: Share via email. Members see the dashboard in their sidebar.
- **Public link**: Generate a read-only URL that anyone can view without logging in. Public dashboards update in real time.
- **Scheduled reports**: Send dashboard snapshots as PDF emails on a daily, weekly, or monthly schedule.

To share, click the **Share** button in the top-right corner of any dashboard.
