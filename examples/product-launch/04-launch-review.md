# Atlas Export Launch Review

Review date: September 8  
Recommendation: Limited beta only

## Passed

- authorization tests cover administrator and non-administrator roles
- workspace-isolation integration suite passed
- 50,000-row and 100,000-row load tests met the five-minute target
- object expiration was verified at seven days
- retry and terminal-failure notifications were exercised

## Open

1. The user interface still says exports remain available for 30 days.
2. The API documentation still advertises a 250,000-record limit.
3. The audit-stream outbox in D-021 is not implemented.
4. No alert exists for a growing failed-job queue.
5. Support has not received a runbook for stuck or repeatedly failing exports.

## Beta boundary

Limit the beta to five workspaces with fewer than 100,000 activity records.
Review failed jobs and audit-stream delivery daily. General availability
requires corrected product copy, operational alerting, a support runbook, and
a decision on whether the audit outbox is mandatory.
