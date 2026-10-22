<div align="center">
  <img src="assets/brand/hcc-logo.png" alt="Home Cinema Control" width="920"/>

<h3>The integrated experience for Emby or Jellyfin, OPPO/Chinoppo, and your cinema room.</h3>

  <p>
    HCC turns one <strong>Play</strong> action in Emby or Jellyfin into a complete room-ready sequence:
    path resolution, player mount, playback, input switching, room control, and progress sync.
  </p>

  <p>
    <img src="https://img.shields.io/github/v/tag/tousled/home-cinema-control?label=version&color=gold&sort=semver" alt="version"/>
    <img src="https://img.shields.io/badge/license-proprietary-lightgrey" alt="proprietary license"/>
    <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="docker"/>
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

## What do you want to do with HCC?

Choose a task and go directly to the relevant guide:

- **Install HCC for the first time:** [follow the step-by-step installation](INSTALL.en.md#2-install-hcc).
- **Update HCC without losing the configuration:** [open the update guide](INSTALL.en.md#13-updating-hcc).
- **Fix a problem:** [open Diagnostics and frequent issues](INSTALL.en.md#10-diagnostics).
- **Recover a configuration:** [review migration and recovery](INSTALL.en.md#4-migration-or-fresh-setup).
- **Configure Emby/Jellyfin, the OPPO, or the
  room:** [follow the setup guide](INSTALL.en.md#5-media-server-emby-or-jellyfin).
- **Check advanced options:** [open the advanced reference](INSTALL.en.md#15-advanced-reference).

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

It also includes an optional telemetry section, disabled by default, to help decide HCC's roadmap: active
installations, selected provider, TV/AV usage, and basic playback events. Telemetry uses a random anonymous
installation ID and never sends paths, IPs, tokens, servers, libraries, titles, logs, scripts, or custom commands. See
[public telemetry documentation](https://github.com/tousled/home-cinema-control/blob/main/docs/telemetry.md).

## Optional Room Control

Some rooms only need Emby and the player. Others need TV input switching, AV receiver power/input control, ARC/CEC
mitigation, and return-to-app behavior after playback.

<p align="center">
  <img src="assets/screenshots/room-setup.png" alt="Home Cinema Control room setup screen" width="860"/>
</p>

TV and AV are configured separately. If disabled, HCC does not instantiate them and does not put them into the playback
flow. Trinnov Altitude is configured here with IP address, MAC address for Wake-on-LAN, and the OPPO source/profile
instead of generic HDMI input names. Automated tests cover this behavior to prevent regressions.

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

| Area                             | Status                                                                                                                                  |
|----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| Emby                             | Implemented as a media-server provider.                                                                                                 |
| Jellyfin                         | Implemented as a media-server provider, same flow as Emby.                                                                              |
| OPPO UDP-203/205                 | Supported through the MediaControl API.                                                                                                 |
| Chinoppo M9702/M9201/M9203/M9205 | Supported when the OPPO-compatible API is exposed.                                                                                      |
| Per-library paths                | NFS or SMB/CIFS per mapping, with verification.                                                                                         |
| LG WebOS TV                      | Input switching and app restore when configured.                                                                                        |
| Sony BRAVIA TV (2013+)           | Input switching and app launch via local REST API (Pre-Shared Key). Contract-tested, pending real-hardware validation.                  |
| AV receivers                     | Denon, Marantz, Yamaha, NAD, Onkyo, Trinnov Altitude, and custom scripts. Trinnov is contract-tested, pending real-hardware validation. |
| Diagnostics                      | Readiness, logs, version, latest failure, and recovery suggestions.                                                                     |
| Telemetry                        | Opt-in, anonymous, documented, and used to prioritize roadmap work.                                                                     |
| Docker                           | Primary deployment path with host networking and persistent `/config`.                                                                  |

## What Defines 1.0.0

1.0.0 is the first stable cut of HCC as an independent product: Emby + OPPO/Chinoppo playback, per-library paths,
optional room control, operational diagnostics, and documented Docker releases. It is not only a visual redesign; it is
the point where setup, support, and updates become part of the product.

| 1.0.0 area                  | What is covered                                                                                                |
|-----------------------------|----------------------------------------------------------------------------------------------------------------|
| Real playback               | MKV, ISO, Blu-ray/UHD folders, stop, replacement, natural end, and recovery validated.                         |
| Watched/resume state        | Coherent progress when playback stops from OPPO, Emby, or the room flow.                                       |
| Interactive sync            | Pause, play, stop, track state, and player status without coupling Emby to OPPO internals.                     |
| Hardware compatibility      | OPPO/Chinoppo, TV, and AVR support documented with clear validated/untested/out-of-scope lines.                |
| Exportable support evidence | Diagnostics, filterable logs, latest failure, support summary, and redacted diagnostic reports sent to GitHub. |
| Docker release path         | Versioned images, rollback, update policy, and proprietary license information.                               |

## Roadmap Direction

After 1.0.0, the architecture is intended to grow without mixing future integrations into the playback core.

| Future area       | Intent                                                                                         |
|-------------------|------------------------------------------------------------------------------------------------|
| Plex              | Explore feasibility after the provider boundary is proven.                                     |
| More TV brands    | Research Samsung, Android TV/Sony, and other ecosystems when hardware validation is possible.  |
| Multiroom         | Explore multiple rooms/players without compromising the current single-room reliability model. |
| Lights and scenes | Possible future room automation, not a requirement for playback.                               |

These items are roadmap direction, not current compatibility claims.

## Home Assistant

HCC can tell Home Assistant when it detects playback, starts it, pauses, resumes, or stops. Home Assistant decides what
to do with each
event: activate a scene, control lights, send an alert, or record it in the logbook.

To set it up, create an automation with a webhook, copy its **Webhook ID** into HCC's **Home Assistant** screen, enable
**Send HCC events to Home Assistant**, save, and restart HCC. The ID is stored securely, never shown in the UI, and
excluded
from diagnostics.

The screen shows the latest real delivery. Before the first event it shows pending; afterwards it shows whether HCC
delivered
the event successfully. If you change the address or webhook, the status returns to pending until the new configuration
works.
If Home Assistant does not respond, HCC records the error and playback continues.

The complete setup, JSON payload, and a conditional automation example are in the
[installation guide](INSTALL.en.md#9-connect-hcc-to-home-assistant).

## Quick Install

Docker Compose is the recommended option: keep `compose.yaml` in its own folder and run the commands from that same
folder. Preserve the `home-cinema-control-config` volume: it contains the configuration and must not be deleted when
updating or recreating the container.

Quick start:

```bash
docker volume create home-cinema-control-config

docker run -d \
  --name home-cinema-control \
  --network host \
  --cap-add NET_RAW \
  --restart unless-stopped \
  -e TZ=Europe/Madrid \
  -e PYTHONUNBUFFERED=1 \
  -e HCC_CONFIG_FILE=/config/config.json \
  -e HCC_SECRETS_FILE_PATH=/config/secrets.json \
  -v home-cinema-control-config:/config \
  ghcr.io/tousled/home-cinema-control:latest
```

Open `http://<your-host>:8090` and follow the setup screens.

For long-running installs, updates, and rollback, Docker Compose is the recommended option:

```yaml
services:
  home-cinema-control:
    image: ghcr.io/tousled/home-cinema-control:${HCC_VERSION:-latest}
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

Read the complete guide in [INSTALL.en.md](INSTALL.en.md).

The [installation guide](INSTALL.en.md) includes screenshots and separate procedures for Docker Compose, Portainer, and
NAS container managers.

## NAS And Player Preparation

HCC does not maintain verified screenshots for every NAS, operating system, or Chinoppo firmware variant. For Synology,
QNAP, Windows, Unraid, and player-side preparation, use the AVPasion Xnoppo community tutorial as an external reference:

https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867

Use that guide for NAS permissions, share setup, and player context. Use this repository's Docker commands,
`HCC_CONFIG_FILE`, `HCC_SECRETS_FILE_PATH`, and web setup for HCC itself.

## Documentation

- [Installation guide](INSTALL.en.md)
- [Spanish installation guide](INSTALL.md)
- [Compatibility](docs/compatibility.md)
- [Telemetry](docs/telemetry.md)
- [Release policy](RELEASE_POLICY.md)
- [Release history](RELEASE_HISTORY.md)
- [Changelog](CHANGELOG.md)
- [Support](SUPPORT.md)
- [Security](SECURITY.md)

## License

HCC is distributed under the **Home Cinema Control Proprietary Software License 2.0**. It is not open-source software, and this license does not grant access to the source code.

Home Cinema Control<br>
Copyright © 2026 Llorente Software Solutions, S.L.<br>
Developed/distributed under the Bytehund brand.

See [LICENSE](LICENSE) for the complete terms.

## Attribution

Home Cinema Control was inspired by the original
[Xnoppo](https://github.com/siberian-git/Xnoppo) idea by **siberian-git** and by the knowledge shared in the AVPasion
community. HCC is an independent implementation built on a new architecture.
