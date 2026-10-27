# Optional pseudonymous telemetry

[Español](telemetry.md) · [How to take part](participate.en.md)

HCC telemetry is optional and disabled by default. An explicit **Help HCC**
action enables sharing. Updates preserve your choice and installation code.
The one-off `telemetry-1.4.3` invitation for prior opt-outs does not enable
sharing unless accepted. Dismissing or declining it prevents another display.
Opening questions does not repeat the invitation or enable consent.

## Data and purpose

The automatic channel sends a random installation code, HCC version, deployment
type, configured media-server/player types, TV provider, and enabled integration
flags. The hub stores an HMAC hash of the code. Signals from the same
installation can be linked: this is pseudonymization, not absolute anonymity.
The network snapshot does not include the AV receiver brand.

Playback events include accepted handoff attempts, pre-handoff rejections,
observed starts, technical closures, failures, permitted diagnostic codes,
operation/phase, and startup timings when available. `event_id` deduplicates
retries; `attempt_id` links events from one playback attempt. A technical
closure does not distinguish natural completion from a manual stop or prove
the exact watched position. Missing events do not prove a failure.

`/ping` sends a technical snapshot on opt-in or meaningful configuration
changes. Equivalent snapshots coalesce. `/heartbeat` sends minimal contact
at most once every 24 hours while consent remains active. Contact does not
prove playback, continued installation, or use of the cinema.

Closed interest votes and question answers are sent only when you save them
with active consent. They help prioritize product decisions without promising
development. Optional free-text suggestions (at most 400 characters) are transmitted only after you explicitly press **Send comment** with consent enabled. Unlike closed questions, these can contain details you write; avoid personal information. The text may temporarily remain in the local retry queue and is stored in the private administrator area of the hub.

Automatic telemetry excludes titles, paths, IPs, hostnames, server names,
libraries, content/session IDs, credentials, tokens, logs, scripts, and custom
commands. Support reports are separate: you choose to review and share them
manually, and they can contain additional diagnostic information.

## Queue and revocation

Failed deliveries use the existing local queue, up to 100 events for seven
days by default. Retries preserve IDs and origin timestamps. A locally saved
answer does not prove receipt, and expired or discarded events cannot be
recovered. Official images include ingestion defaults. Custom deployments
can override them with `HCC_TELEMETRY_ENDPOINT_URL` and
`HCC_TELEMETRY_INGEST_KEY`, or the matching telemetry configuration fields.
Precedence is deployment environment, configuration, then image defaults.

Disabling sharing blocks new delivery, cancels asynchronous work, and clears
the persistent queue. HCC makes one best-effort `install_opt_out` request
with the same code, without storing or retrying it. If offline, the hub may
never observe revocation. Revocation does not delete data already received.
Reopening questions does not replay saved answers.

## Question contract

`question_answer_submitted` uses the existing v4 `/event` envelope with a
stable `event_id`. `occurred_at` equals `attributes.submitted_at`, including
a timezone, and both remain unchanged on retry.

| Attribute          | Type         | Allowed value                                                            |
|--------------------|--------------|--------------------------------------------------------------------------|
| `question_id`      | string       | `emby_jellyfin_priorities`, `playback_entrypoint`, `next_media_player`                                               |
| `question_version` | integer      | `1`                                                                      |
| `catalog_version`  | integer      | `1` or `2`                                                                      |
| `option_ids`       | string array | `use_both_servers`, `sync_history`, `browse_both_catalogs`, `not_needed` |
| `submitted_at`     | string       | Original timestamp with timezone                                         |

Selections cannot be empty or contain duplicates. `not_needed` excludes other
options. The receiver rejects unknown fields, questions, versions, and options.
It keeps answer history and counts the last received answer per installation
and question, using receipt order rather than trusting the client clock.
Aggregates distinguish response events, unique installations, and current
answers. Legacy interest events remain compatible.

The catalog ships with HCC. Adding questions remotely without another HCC
version would require a separate product decision. Local seen, answered,
postponed, and dismissed states persist by question ID, including retired
answers. A new question does not overwrite an earlier response.

## Deployment dependency

A compatible receiver must be deployed and validated before enabling the
question producer. Verify synthetic answers, retries, edits, invalid
combinations, legacy votes, consent, and revocation in an authorized test
environment. Preserve origin and receipt timestamps separately. Missing or
invalid origin time in legacy events remains explicitly unknown.
Implementing these changes does not authorize deployment, NAS production
changes, or a release.
