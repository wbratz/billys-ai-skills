# Atlas Export PRD

Status: Approved  
Owner: Product  
Target launch: September 15

## Problem

Operations teams need a weekly export of project activity for internal audit.
Today they assemble reports manually from several screens.

## Requirements

1. Workspace administrators can export the previous 90 days of activity.
2. Exports are delivered as CSV within five minutes.
3. A completed export remains downloadable for 30 days.
4. Every export request and download is written to the audit log.
5. The first release supports workspaces with up to 250,000 activity records.

## Success measures

- 95 percent of exports complete within five minutes.
- Fewer than 2 percent of export attempts fail.
- Support receives no confirmed cross-workspace data exposure reports.

## Explicitly out of scope

- scheduled exports
- custom date ranges
- formats other than CSV
- exports larger than 250,000 records
