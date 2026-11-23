# Optional pseudonymous telemetry

[Español](telemetry.md) · [How to take part](participate.en.md)

HCC telemetry is optional and disabled by default. An explicit **Help HCC**
action enables sharing. Updates preserve your choice and installation code.
The one-off `telemetry-1.4.3` invitation for prior opt-outs does not enable
sharing unless accepted. Dismissing or declining it prevents another display.
Opening questions does not repeat the invitation or enable consent.

## Samsung compatibility

In **Room**, **Help improve Samsung compatibility** authorises an independent category. It is off by default and is
not required to use your TV. Enabling it creates a random installation ID if needed, or reuses your existing ID.
Enabling general telemetry later keeps that same ID.

With only Samsung compatibility enabled, HCC shares only that category: the commercial model detected through the
TV's local API, control operation and strategy, technical result, **Yes/No/I don't know** picture observations,
bounded error codes, and HCC version. Random event/test identifiers and timestamps correlate technical replies with
observations and deduplicate retries. IP addresses, MACs, serial numbers, custom names, certificates, credentials,
complete TV replies, and movie or media-server information are excluded.

There is no model form or manual report. If HCC cannot identify the model, it records unknown. Enabling the option
may also share valid checks you already saved; collection does not switch inputs, change power, or open apps.
A command accepted by the TV is kept separate from a picture confirmed by the user.

With both options enabled, both categories are shared. Disabling either preserves the other. Disabling Samsung
compatibility stops new deliveries and clears its pending queue, while keeping your TV settings and checks.
An in-flight delivery finishes before deactivation is confirmed; no new deliveries for that category start afterwards.
Revocation does not automatically delete reports already received by the Hub.

The receiver must support the Samsung compatibility contract. HCC checks that capability before sending and keeps
reports in their separate retry queue if the Hub does not yet support it. The private dashboard separates models,
operations, attempts, contributing installations, and picture confirmations. Missing samples do not mean
incompatibility.

## Data and purpose

The automatic channel sends a random installation code, HCC version, deployment
type, configured media-server/player types, TV provider, and enabled integration
flags. The hub stores an HMAC hash of the code. Signals from the same
installation can be linked: this is pseudonymization, not absolute anonymity.
With general telemetry enabled, the `/ping` configuration snapshot may
include the **allowlisted AV receiver brand** when configured and enabled
(Denon, Marantz, NAD, Onkyo, Yamaha, or scripts). It does not send the
free-form model name, IP address, or credentials. Samsung is also recognized
as an allowlisted TV provider.

Playback events include accepted handoff attempts, pre-handoff rejections,
observed starts, technical closures, failures, permitted diagnostic codes,
operation/phase, and startup timings when available. `event_id` deduplicates
retries; `attempt_id` links events from one playback attempt. A technical
closure does not distinguish natural completion from a manual stop or prove
the exact watched position. Missing events do not prove a failure.

`/ping` includes the room wiring layout (`split_av_tv`, `via_avr`, `direct_tv`, or `unknown`) only when telemetry
participation is enabled. It does not include IP addresses, ports, or HDMI input names. Existing installations without
an explicit selection are reported as `unknown`.

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

## Optional automatic playback diagnostics (1.4.4 hotfix)

The **Diagnostics** screen has a separate opt-in checkbox for automatic
playback diagnostics. It defaults to **off**, even for users who already
enabled basic telemetry. You can turn it off at any time: pending diagnostic
events are dropped, and disabling basic telemetry resets this choice too.

When enabled, a failed handoff may produce an additional
`playback_diagnostic` event with a recognized error code, a short closed-set
step trace, NFS/SMB protocol when known, elapsed time and the result of
**room/error recovery**. A successful room restoration does not mean playback
started. This opt-in does **not** transmit raw logs, exceptions, IP addresses,
media titles, file or library paths, credentials, custom commands, or arbitrary
messages.

Diagnostics are separate from playback outcomes; they do **not** increase the
playback failure rate. A transient problem successfully recovered within the
same attempt remains a successful start. Later cleanup problems do not undo
an observed playback start. Details are available in the private installation
event history.

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

### Local delivery diagnostics (1.5.0)

The local `GET /api/v1/telemetry` endpoint includes `delivery_diagnostics`: aggregate counters for events accepted by
the asynchronous worker, delivered over HTTP, persisted for retry, transport errors, asynchronous queue overflows, and
persistence failures. The `playback` section separates attempts, starts, finishes, failures, and rejections to help
locate missing playback observations.

These counters **cover the current process only** and reset after HCC restarts. A "delivered" event indicates a
non-error HTTP response, not proof that the hub counted it. The persistent retry queue remains available through
`queue_count` and can include events from a previous process.

Diagnostics are exposed **locally only**. They are never transmitted to the hub and contain no installation IDs, titles,
IP addresses, URLs, keys, paths, or content identifiers. Consent is still required for telemetry delivery. Unexpected
transport exceptions now preserve events in the retry queue when it is writable; local persistence failures are logged
and counted because discarded events cannot be reconstructed.


## Experimental OPPO Blu-ray resume and upgrades from 1.4.6

Blu-ray resume does not require general telemetry or any other data-sharing
permission. Existing playback settings are preserved on upgrade and after
telemetry opt-out. No new Blu-ray-specific outcomes are sent, even when
basic telemetry is enabled. Users may voluntarily provide troubleshooting
information through the support channels if necessary.
