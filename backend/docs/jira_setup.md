# Jira Setup Guide for NOC Agent

## Prerequisites

- Jira Cloud or Data Center (tested on Cloud)
- Admin access to the Jira project

---

## Step 1: Create the Project

1. Go to **Projects → Create project**
2. Choose **Scrum** or **Kanban** (or your existing project)
3. Project key: `NOC` (or set `JIRA_PROJECT_KEY` in `.env`)

---

## Step 2: Create Custom Fields

Go to **Jira Settings → Issues → Custom Fields → Add custom field**.

Create the following fields:

| Field Name | Type | Notes |
|---|---|---|
| `NOC Incident ID` | Text Field | Store our internal UUID |
| `NOC Category` | Select List (single) | Options: physical, data_integrity, coupling |
| `NOC Confidence` | Number Field | 0–100 |
| `NOC Hypothesis` | Text Field (multi-line) | Agent's hypothesis text |
| `NOC Suggested Action` | Text Field | Action key from allowlist |
| `NOC Resolution Category` | Select List (single) | See options below |
| `NOC Was Hypothesis Correct` | Select List (single) | Options: yes, partially, no |
| `NOC Actual Resolution Details` | Text Field (multi-line) | Free text |

**Resolution Category options:**
- hardware_replacement
- config_change
- restart_service
- cache_clear
- scheduled_maintenance
- false_positive
- upstream_issue
- requires_investigation
- environmental
- network_peer
- software_bug
- capacity

---

## Step 3: Add Fields to Screen

1. Go to **Jira Settings → Issues → Screens**
2. Find your project's **Default Screen** (or create one)
3. Add all `NOC *` custom fields to the screen

---

## Step 4: Make Resolution Fields Required

1. Go to **Jira Settings → Issues → Workflows**
2. Edit your project's workflow
3. On the **Resolve** transition: add a **Validator** → **Field Required**
4. Add these fields as required:
   - `NOC Resolution Category`
   - `NOC Was Hypothesis Correct`
   - `NOC Actual Resolution Details`

This ensures engineers fill in feedback before closing tickets.

---

## Step 5: Configure Webhook (back to NOC Agent)

1. Go to **Jira Settings → System → WebHooks**
2. Create a new webhook:
   - URL: `https://your-noc-agent.domain/api/v1/webhooks/jira`
   - Events: **Issue Updated**, **Issue Resolved**
   - JQL filter: `project = NOC`

---

## Step 6: Update `.env` with Field IDs

After creating custom fields, find each field's ID:

1. Go to **Jira Settings → Issues → Custom Fields**
2. Click a field → **View Field Information** → note the ID (e.g. `customfield_10042`)

Update `.env`:
```env
JIRA_URL=https://yourcompany.atlassian.net
JIRA_USER=your-email@company.com
JIRA_TOKEN=your-api-token
JIRA_PROJECT_KEY=NOC
JIRA_ISSUE_TYPE=Task
JIRA_CUSTOM_FIELD_IDS={"incident_id":"customfield_10042","category":"customfield_10043",...}
```

---

## Step 7: Generate API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create API token
3. Add to `.env` as `JIRA_TOKEN`

---

## Testing

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/grafana \
  -H "Content-Type: application/json" \
  -d '{"receiver":"test","status":"firing","alerts":[{"status":"firing","labels":{"alertname":"TestCPU","hostname":"srv-01","severity":"critical","category":"physical"},"annotations":{},"startsAt":"2024-01-01T10:00:00Z","fingerprint":"test123","values":{"A":95.0},"startsAt":"2024-01-01T10:00:00Z","endsAt":"0001-01-01T00:00:00Z","generatorURL":""}]}'
```

Check Jira for the newly-created `NOC-*` ticket.
