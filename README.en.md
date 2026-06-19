<div align="center">
  <img src="assets/brand/hcc-logo.png" alt="Home Cinema Control" width="920"/>

<h3>The integrated experience for Emby, OPPO/Chinoppo, and your cinema room.</h3>

  <p>
    HCC turns one <strong>Play</strong> action in Emby into a complete room-ready sequence:
    path resolution, player mount, playback, input switching, room control, and progress sync.
  </p>

  <p>
    <img src="https://img.shields.io/badge/version-1.0.0-rc.1-gold" alt="version"/>
    <img src="https://img.shields.io/badge/license-source--available-lightgrey" alt="license"/>
    <img src="https://img.shields.io/badge/python-3.14-blue" alt="python"/>
    <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="docker"/>
    <img src="https://img.shields.io/badge/Vue_3-FastAPI-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue 3 and FastAPI"/>
  </p>

  <p>
    <a href="README.md">Español</a> ·
    <a href="INSTALL.en.md">Installation</a> ·
    <a href="LICENSE">License</a> ·
    <a href="CHANGELOG.md">Changelog</a>
  </p>
</div>

---

Home Cinema Control exists so a home cinema stops feeling like a pile of disconnected devices.

Emby is a great media library. OPPO UDP-203/205 and Chinoppo M9xxx players are excellent for local high-bitrate files,
ISOs, Blu-ray/UHD folders, and NAS playback. The missing piece is the integrated experience: correct paths, HDMI inputs,
NFS/SMB mounts, room automation, diagnostics, and progress tracking working as one flow.

HCC connects those pieces. You pick a movie in Emby; the room prepares itself for playback.

## Problems HCC Tries To Solve

HCC builds on years of real-world use, repeated forum questions, and hard-to-diagnose failures in setups involving Emby,
NAS shares, OPPO/Chinoppo players, TVs, and AV receivers. The goal is to reduce the places where users had to guess.

- **Clearer install and migration**: Docker-first deployment, `HCC_*` variables, separated secrets, and a migration
  screen for older configurations.
- **Less manual path typing**: Emby library discovery, guided mapping, and manual mode when a specific setup needs it.
- **NFS and SMB/CIFS per library**: each mapping declares the protocol the player should use.
- **Testing before playback**: HCC tests mappings through the OPPO/Chinoppo before a real viewing session.
- **Easier device discovery**: when `arp-scan` is available, the UI suggests detected LAN IP addresses.
- **Truly optional TV and AV**: disabled room devices do not enter the playback flow.
- **More predictable startup and exit**: HCC separates authentication, path, mount, player, TV, and AV failures instead
  of leaving users with a black screen or a generic playback failure.
- **Better Emby/OPPO synchronization**: HCC observes player state so pause, play, stop, natural end, progress, and track
  selection can be reflected back when firmware support allows it.
- **Readable logs and diagnostics**: severity, latest failure, suggestions, and support summary are visible in the UI.
- **Fewer manual regressions**: simulated tests cover path selection, protocol decisions, and disabled TV/AV flows.

## What Happens When You Press Play

1. Emby starts a playback session.
2. HCC checks whether the selected library should be intercepted.
3. HCC resolves the verified mapping from the Emby path to the player-visible path.
4. The OPPO/Chinoppo mounts the selected NFS or SMB share.
5. The hardware player starts the real file.
6. TV and AV control run only if configured.
7. HCC observes progress, pause, stop, natural end, errors, and session cleanup.
8. Emby receives the state needed to keep watched/resume behavior coherent.

Emby remains the library. The OPPO/Chinoppo remains the player. HCC coordinates the room.

## Diagnostics Instead Of Guesswork

The Status screen is where HCC shows readiness, current playback state, failures, logs, version status, and support
information.

<p align="center">
  <img src="assets/screenshots/status.png" alt="Home Cinema Control diagnostics screen" width="860"/>
</p>

The purpose is to turn “try again” into actionable information: Emby issue, unverified route, OPPO mount failure,
disabled room device, or deployment/update problem.

## Optional Room Control

Some rooms only need Emby and the player. Others need TV input switching, AV receiver power/input control, ARC/CEC
mitigation, and return-to-app behavior after playback.

<p align="center">
  <img src="assets/screenshots/room-setup.png" alt="Home Cinema Control room setup screen" width="860"/>
</p>

TV and AV are configured separately. If disabled, HCC does not instantiate them and does not put them into the playback
flow. Automated tests cover this behavior to prevent regressions.

## Improvements You Feel Even When You Do Not See Them

HCC also improves the parts a normal user should not have to inspect, but that make the setup feel more serious.

| Improvement                        | User benefit                                                                                                                                                                                        |
|------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| SVM3 observation by default        | HCC tries to listen to OPPO events instead of always asking for state every second. The player sees less noise, and HCC still keeps a bounded polling fallback when firmware support is not enough. |
| Less aggressive progress reporting | Playback position is reported to Emby on a controlled cadence, not through unnecessary constant queries.                                                                                            |
| Explicit NFS/SMB routes            | Each library uses the protocol you tested. There is no silent switch that works once and fails during the important session.                                                                        |
| Section-scoped saves               | Changing room setup does not overwrite Emby settings, and saving paths does not rewrite secrets unnecessarily.                                                                                      |
| Credentials kept out of logs       | SMB passwords are not exposed in logged request URLs or support traces.                                                                                                                             |
| Diagnostics before mystery         | When something fails, HCC tries to name the failing component: Emby, path, OPPO, TV, AV, update, or cleanup.                                                                                        |
| Wiring tests                       | Disabled TV/AV, per-library protocols, and partial setup saves have automated tests to prevent regressions.                                                                                         |

## Current Scope

| Area                             | Status                                                                 |
|----------------------------------|------------------------------------------------------------------------|
| Emby                             | Implemented as the primary media-server provider.                      |
| OPPO UDP-203/205                 | Supported through the MediaControl API.                                |
| Chinoppo M9702/M9201/M9203/M9205 | Supported when the OPPO-compatible API is exposed.                     |
| Per-library paths                | NFS or SMB/CIFS per mapping, with verification.                        |
| LG WebOS TV                      | Input switching and app restore when configured.                       |
| AV receivers                     | Denon, Marantz, Yamaha, NAD, Onkyo, and custom scripts.                |
| Diagnostics                      | Readiness, logs, version, latest failure, and recovery suggestions.    |
| Docker                           | Primary deployment path with host networking and persistent `/config`. |

## What Defines 1.0.0

1.0.0 is the first stable cut of HCC as an independent product: Emby + OPPO/Chinoppo playback, per-library paths,
optional room control, operational diagnostics, and documented Docker releases. It is not only a visual redesign; it is
the point where setup, support, and updates become part of the product.

| 1.0.0 area                  | What is covered                                                                                 |
|-----------------------------|-------------------------------------------------------------------------------------------------|
| Real playback               | MKV, ISO, Blu-ray/UHD folders, stop, replacement, natural end, and recovery validated.          |
| Watched/resume state        | Coherent progress when playback stops from OPPO, Emby, or the room flow.                        |
| Interactive sync            | Pause, play, stop, track state, and player status without coupling Emby to OPPO internals.      |
| Hardware compatibility      | OPPO/Chinoppo, TV, and AVR support documented with clear validated/untested/out-of-scope lines. |
| Exportable support evidence | Diagnostics, filterable logs, latest failure, and support summary from the UI.                  |
| Docker release path         | Versioned images, rollback, update policy, and source-available license clarity.                |

## Roadmap Direction

After 1.0.0, the architecture is intended to grow without mixing future integrations into the playback core.

| Future area       | Intent                                                                                         |
|-------------------|------------------------------------------------------------------------------------------------|
| Jellyfin          | Add a second media-server provider once the provider contract is stable and tested.            |
| Plex              | Explore feasibility after the provider boundary is proven.                                     |
| More TV brands    | Research Samsung, Android TV/Sony, and other ecosystems when hardware validation is possible.  |
| Multiroom         | Explore multiple rooms/players without compromising the current single-room reliability model. |
| Lights and scenes | Possible future room automation, not a requirement for playback.                               |

These items are roadmap direction, not current compatibility claims.

## Quick Install

HCC runs as a Docker container with host networking.

```yaml
services:
  home-cinema-control:
    image: ghcr.io/tousled/home-cinema-control:latest
    container_name: home-cinema-control
    network_mode: host
    cap_add:
      - NET_RAW
    restart: unless-stopped
    environment:
      TZ: Europe/Madrid
      PYTHONUNBUFFERED: "1"
      HCC_CONFIG_FILE: /config/config.json
      HCC_SECRETS_FILE_PATH: /config/secrets.json
    volumes:
      - home-cinema-control-config:/config

volumes:
  home-cinema-control-config:
    name: home-cinema-control-config
```

```bash
docker compose pull
docker compose up -d
```

Open `http://<your-host>:8090` and follow the setup screens.

Read the complete guide in [INSTALL.en.md](INSTALL.en.md).

## NAS And Player Preparation

HCC does not maintain verified screenshots for every NAS, operating system, or Chinoppo firmware variant. For Synology,
QNAP, Windows, Unraid, and player-side preparation, use the AVPasion Xnoppo community tutorial as an external reference:

https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867

Use that guide for NAS permissions, share setup, and player context. Use this repository's `compose.yaml`,
`HCC_CONFIG_FILE`, `HCC_SECRETS_FILE_PATH`, and web setup for HCC itself.

## Documentation

- [Installation guide](INSTALL.en.md)
- [Spanish README](README.md)
- [Guía de instalación](INSTALL.md)
- [Release policy](RELEASE_POLICY.md)
- [License](LICENSE)
- [Changelog](CHANGELOG.md)

## License

HCC is **source-available**, not open source. The code is visible for review,
learning, evaluation, and personal non-commercial use, but commercial use,
redistribution, published images/packages, managed hosting, and sale of
derivative works are not permitted without written permission. See
[LICENSE](LICENSE).

## Attribution

Home Cinema Control was inspired by the original
[Xnoppo](https://github.com/siberian-git/Xnoppo) idea by **siberian-git** and by the knowledge shared in the AVPasion
community. HCC is an independent implementation built on a new architecture.
