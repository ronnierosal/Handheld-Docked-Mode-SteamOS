# Secure support-bundle submission design

Support submission is not enabled. HDM currently previews, copies, and saves a
bundle locally. This document defines the later security boundary without
embedding a server address, credential, upload token, or network adapter.

## Separate approval

Logging consent, local save consent, and upload consent are independent. A
future **Submit** action must issue a new five-minute, single-use approval bound
to the exact UTF-8 bytes the player already reviewed. Consumption returns only:

- exact body bytes
- `application/json`
- byte length, at most 256 KiB
- SHA-256 checksum

No endpoint, path, filename, account identity, R2 key, bearer token, or cloud
credential is accepted from the frontend or stored in this approval object.

## Worker contract

The future deployment should use one backend-owned HTTPS endpoint:

```text
HDM -> HTTPS -> narrowly scoped Cloudflare Worker -> private R2 bucket
```

The Worker must:

- accept only `POST` with exact `application/json`
- enforce the encoded size limit before parsing
- validate bundle schema and checksum
- reject unknown top-level fields where the protocol specifies a closed shape
- rate-limit and apply abuse controls before R2 writes
- generate the R2 object key and non-guessable report ID server-side
- never accept a client filesystem/object path
- store uploads in a private bucket with a roughly 30-day lifecycle policy
- have only the minimum R2 write permission needed for that bucket/prefix
- never execute, unpack, render, or serve submitted content as active content
- return only `{ "ok": true, "report_id": "HDM-..." }`
- record an auditable categorical outcome without copying bundle contents into
  general Worker logs

The client parser accepts only the exact success response and a bounded
`HDM-[A-Z0-9]` report ID. Redirect URLs, object URLs, extra fields, and
client-chosen IDs are rejected.

## Current boundary

The approval store, checksum/size revalidation, strict response parser, and an
unimplemented fixed-configuration port are unit tested. There is no HTTP client,
Worker project, R2 bucket, endpoint, DNS, credential, public RPC, or UI action.
Creating cloud resources and choosing production abuse/rate-limit settings
require a separate deployment decision and account authorization.
