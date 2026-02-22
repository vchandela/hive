# Setting Up Alerts

## Alert Rules

Alerts notify you when your data meets specific conditions. They run on a schedule and trigger notifications when thresholds are crossed.

To create an alert:

1. Go to **Alerts** in the left sidebar.
2. Click **New Alert**.
3. Write a query that returns a numeric value.
4. Set the condition: `greater than`, `less than`, `equals`, or `changes by more than X%`.
5. Set the threshold value.
6. Choose the check frequency: every 1, 5, 15, or 60 minutes.

Example: alert when error rate exceeds 5%:

```sql
SELECT count(CASE WHEN status >= 500 THEN 1 END) * 100.0 / count(*) as error_rate
FROM api_logs
WHERE timestamp > now() - interval '5 minutes'
```

Condition: `error_rate greater than 5.0`

## Notification Channels

Alerts can notify through multiple channels:

- **Email**: Sent to individual users or distribution lists.
- **Slack**: Post to a Slack channel via incoming webhook. Configure in Settings > Integrations.
- **PagerDuty**: Trigger incidents for critical alerts. Requires a PagerDuty integration key.
- **Webhook**: Send a JSON payload to any HTTPS endpoint.

You can assign multiple channels to a single alert. Each channel can have its own severity level (info, warning, critical).

## Escalation

For critical alerts, configure escalation policies:

1. **Level 1**: Notify the primary on-call via Slack (immediate).
2. **Level 2**: If not acknowledged within 15 minutes, notify via PagerDuty.
3. **Level 3**: If not acknowledged within 1 hour, email the team lead.

Escalation policies ensure alerts don't get lost. Acknowledgment can be done via Slack reaction, PagerDuty, or the DataStack dashboard.
