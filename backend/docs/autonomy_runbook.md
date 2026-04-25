# Autonomy Runbook

## Overview
The NOC system supports graded autonomous remediation. Actions are only executed automatically when all gates pass.

## Gates (in order)
1. **Global kill switch** — set via `POST /api/v1/autonomy/kill-switch {"enabled": true}` to disable all autonomous execution
2. **Tier assignment** — action must have `autonomous_tier >= 1` in `action_tier_config`
3. **Confidence threshold** — investigation confidence must be ≥ 80%
4. **Circuit breaker** — no more than 3 failures per (action, host) in 1 hour

## Tier Levels
| Tier | Meaning |
|------|---------|
| 0 | Manual only (default) |
| 1 | Autonomous for low-risk actions (>= 10 uses, >= 85% accuracy) |
| 2 | Autonomous for medium-risk (>= 30 uses, >= 92% accuracy) |

## Promotion Workflow
1. Check `/api/v1/metrics/autonomy-candidates` for qualifying actions
2. Review action history at `/api/v1/autonomy/audit`
3. Promote via `POST /api/v1/actions/{action_key}/promote`
4. Monitor shadow queue at `/api/v1/autonomy/shadow-queue`

## Emergency Procedures

### Disable all autonomous execution immediately
```
POST /api/v1/autonomy/kill-switch
{"enabled": false}
```
Or set Redis key `autonomy:kill_switch = 1`.

### Roll back a specific action
```
POST /api/v1/autonomy/rollback/{action_id}
```
The response includes the specific rollback procedure for the action type.

### Demote an action (stop autonomous execution)
Use TierManager.demote() or set `autonomous_tier = 0` in `action_tier_config`.

## Audit Trail
Every autonomous decision (executed or shadow) is recorded in `autonomous_actions` and `shadow_mode_decisions` tables respectively. These are append-only.

## Default Configuration
- `AUTONOMY_ENABLED = false` — autonomy is off by default
- All actions start at Tier 0
- Shadow mode runs for all qualifying decisions regardless of kill switch
