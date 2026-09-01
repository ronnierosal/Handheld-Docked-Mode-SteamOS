# Offline Readiness UI

Status: **Implemented (read-only presentation); Source review and delivery
wiring required**

Quick Access can present only the existing public Offline Readiness categories:
**Ready to try offline**, **Needs attention**, **Online check needed**, and
**Unknown**. “Ready to try” is deliberately not a promise that a game will
launch or play offline.

The optional payload accepts only schema version, categorical status, and public
reason codes. It has no title, AppID, account, path, timestamp, or collector
command fields. The UI does not render raw reason codes, and unknown/missing
delivery remains a fail-closed “Not connected” status.

There is still no Steam/launcher collector, persistence, launch authority, or
new polling loop. A future source must be reviewed, local-only,
identity-minimized, benchmarked, bounded-cost, and freshness-gated before a
read-only adapter may supply this payload.
