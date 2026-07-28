# Atlas Export Decision Log

## D-014: Reduce first-release record limit

Decision: ship with a 100,000-record limit instead of 250,000.

Reason: load testing showed the five-minute product target was missed above
roughly 140,000 records. The team chose a smaller supported boundary rather
than presenting an unreliable promise.

Follow-up: move CSV assembly to multipart streaming, then rerun the 250,000-row
test before expanding the limit.

## D-018: Shorten download retention

Decision: expire generated exports after seven days instead of thirty.

Reason: the security review classified activity exports as sensitive derived
data. Seven days was enough for the observed workflow and reduced exposure.

Follow-up: Product must update launch copy and the in-product expiration label.

## D-021: Defer durable download-audit confirmation

Decision: keep download-event publication asynchronous for the first release.

Reason: blocking downloads on the audit stream made the download endpoint
dependent on an unrelated service.

Follow-up: add a replayable outbox before general availability. Until then,
stream interruption can delay or lose a download event.
