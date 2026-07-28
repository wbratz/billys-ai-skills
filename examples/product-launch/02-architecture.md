# Atlas Export Architecture

Status: Implemented in release candidate

## Flow

1. The API validates that the requester is a workspace administrator.
2. It writes an export job containing the workspace identifier and a snapshot
   timestamp.
3. A worker reads activity records in 10,000-row pages and writes a compressed
   CSV object.
4. The object store creates a signed download URL.
5. A notification tells the requester that the export is ready.

## Operating boundaries

- Jobs stop after ten minutes.
- A workspace may have two export jobs in progress.
- Generated objects expire after seven days.
- The worker supports 100,000 records in the release candidate.
- Download events are sent asynchronously to the audit stream.

## Isolation

Every database page includes the workspace identifier in its query. The object
key also includes the workspace identifier and export job identifier. Signed
URLs expire after fifteen minutes.

## Failure behavior

The worker retries transient database and object-store failures three times.
After the final failure it marks the job failed and sends a notification.
