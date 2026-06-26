# CONTEXT — Domain glossary

Domain vocabulary for Home Cinema Control. Architecture reviews
(`/improve-codebase-architecture`) read this file to name seams after concepts
that already exist. Decisions are recorded in `.agents/adr/`.

## Integration principle (applies to every external system)

This is the root principle. It is **not** specific to media servers — it governs
every external system HCC talks to: media servers (Emby/Jellyfin/Plex), TVs, AV
receivers, media players (OPPO), and any future integration. The sections below
(media servers, TV, AV, players) are *instances* of this one pattern.

**Integration adapter** — HCC's anti-corruption adapter for one external system.
The HCC core never speaks the external system's language; it speaks only HCC
domain. Each adapter owns that system's transport, protocol, and wire-format
mappers. Adapters never import each other. See
[ADR-0001](.agents/adr/0001-external-system-anti-corruption-layer.md).

**Adapter edge** — the seam where external wire format (raw JSON `dict`, TCP
command string, device response) is mapped to/from HCC domain objects. Raw wire
shapes — external field names, message types, command strings — must not cross
this edge into shared policy.

**Inbound mapper** — external response / event → HCC domain object. Lives at the
adapter edge (e.g. `media_servers/*/session_events.py`, `track_mapping.py`).

**Outbound mapper** — HCC domain object → external request → external transport
client. Lives in the adapter's client / reporting code.

**Port** — a `Protocol` the HCC core depends on, implemented by adapters at a
seam (`playback/ports.py`: `TelevisionOutputPort`, `AvReceiverOutputPort`,
`OppoPlaybackPort`, `MediaPlayerPort`). The outbound side of the integration
principle. Suffix taxonomy for ports/adapters/commands: see
[ADR-0002](.agents/adr/0002-naming-suffix-taxonomy.md).

**Shared policy** — provider-neutral HCC logic that operates only on domain
objects (handoff decision, command translation to a port, listener
wiring/routing, library reconciliation). Sharing is decided by **altitude**:
domain-level policy is shared; wire-format handling stays per-adapter. The
"don't share because two payloads look similar" rule applies to wire-format
handling only.

## Media servers (instance of the integration principle)

**Media server** — the source of truth for the user's library and playback
sessions: Emby, Jellyfin, and (future) Plex. HCC controls one active media
server per installation.

**Provider** — the integration adapter for one media server, under
`media_servers/<name>/`. Owns that server's HTTP client, websocket transport,
auth headers, routes, and JSON mappers.

### Domain objects (HCC language for media servers)

**`PlaybackIntent`** (`playback/intent.py`) — "start or recover *this*
playback": media item, source, start position, selected tracks, origin device.
Produced by both the observed-session path and the `Play`/`PlayNow` command path.
The handoff request the playback pipeline acts on.

**`MediaServerSession`** — an observed session the media server reports: monitored
device, now-playing item, playstate. The domain object the session monitor
reasons over instead of a raw session `dict`.

**`MediaServerCommand`** — an in-playback control instruction issued by the media
server: seek, pause/unpause, track change, stop. Distinct from `PlaybackIntent`:
intent *starts* playback, command *mutates* playback already in progress.

**`MediaServerLibrary`** (`common/models.py`) — a library as HCC needs it
(`id`, `name`, `active`), with `reconciled_with` preserving the user's choices.
Providers map their own API shape into it.

**`MediaServerDevice`** (`common/models.py`) — a controllable playback device
discovered from the media server.

## TV, AV receivers, media players (instances of the integration principle)

Same pattern, different external system. Each owns its transport and mappers and
is reached through a port; the HCC core stays in domain language.

**`TelevisionOutputPort`**, **`AvReceiverOutputPort`** (`playback/ports.py`) —
the outbound ports for TV and AV-receiver control. Adapters (LG, Denon, Marantz,
NAD, Scripts, …) are selected by their factories.

**`OppoPlaybackPort` / `MediaPlayerPort`** (`playback/ports.py`) — the outbound
ports to the OPPO player: mount/playback and command/control (seek, remote key,
track select). The OPPO command handler is where the media-server inbound ACL
meets this outbound port. (`MediaPlayerControl` was renamed to `MediaPlayerPort`
per [ADR-0002](.agents/adr/0002-naming-suffix-taxonomy.md).)

**OPPO QPL** — the authoritative playback-state signal from the OPPO player.
**SVM3** — the OPPO verbose event stream; must not be active during stable
startup. (See `src/AGENTS.md` "Key invariants".)
