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

**[See HCC in action: 45-second demonstration](assets/videos/hcc-demo.mp4)**

Home Cinema Control connects your Emby or Jellyfin library with your player and room devices. Choose a movie in your
usual app: HCC prepares playback on the selected player, coordinates the TV and AV receiver inputs you configured, and
reports progress to the media server.

The video shows a supported room setup; it does not guarantee identical features on every device.

> Documentation prepared for the future **1.5.0**, which is not published yet. The latest published stable release is
> **1.4.5**. The Kodi features described here belong to 1.5.0; installing `latest` does not add them before publication.

## What do you want to do with HCC?

Choose the guide for your task:

- [Install HCC with Portainer or Docker Compose](INSTALL.en.md).
- [Set up Emby/Jellyfin, OPPO or Kodi and play your first movie](docs/getting-started.en.md).
- [Match media-server folders to player folders](docs/configure-media-paths.en.md).
- Update without losing settings: [Portainer](docs/update-portainer.en.md)
  or [Docker Compose](docs/update-compose.en.md).
- [Recover a configuration that appears to have disappeared](docs/recover-configuration.en.md).
- [Resolve a problem and get help](docs/troubleshoot.en.md).
- Look up [advanced settings](docs/advanced-reference.en.md)
  or [backups and Docker operations](docs/advanced-docker-operations.en.md).

## What happens when you press Play

1. Open Emby or Jellyfin on the device you selected for HCC to monitor and choose a movie.
2. HCC checks the player and configured folder before preparing your room and handing over playback.
3. The player opens the movie from your NAS or shared folder. HCC follows its state and updates progress on the media
   server.
4. When playback ends, HCC applies your configured closing actions. If you use Home Assistant, HCC can also send
   playback events to your automations.

TV, AV receiver, and Home Assistant setup is optional. Start with the media server, player, and folders, then add the
rest later.

## Supported equipment

Each device keeps its role: Emby/Jellyfin organises your library, and the player opens files from your network.

| Equipment                    | Support                                                                                                                              |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| Media server                 | Emby or Jellyfin; select the device whose playback HCC should monitor.                                                               |
| OPPO/Chinoppo                | OPPO UDP-203/205 and clones with compatible network control. NFS or SMB folders; available options depend on firmware.               |
| Kodi, from HCC 1.5.0         | HTTP control and NFS/SMB folders configured in Kodi. HCC can browse and test them, then start and monitor playback.                  |
| TV and AV receiver, optional | LG webOS, Sony BRAVIA, and receiver brands offered in Room. Trinnov Altitude has contract tests but awaits real-hardware validation. |
| Home Assistant, optional     | Receives events for the automations you configure.                                                                                   |

For Kodi, start with a regular video file such as MKV. Format support depends on Kodi and its device; the same ISO,
Blu-ray folder, or disc-menu experience as OPPO is not guaranteed. Local Kodi folders are outside 1.5.0 and reserved for
a later 1.5.x update, with no announced date. Sources using `plugin://` or protocols other than NFS/SMB are also
unsupported.

Kodi has an optional power-setup wizard. Automatic mode requires verified shutdown and wake; unverified experimental
shutdown requires explicit opt-in and manual wake. Support depends on the device and still needs physical validation.
See [first steps](docs/getting-started.en.md).

HCC keeps OPPO and Kodi settings and media paths separately. Switch between players to recover your previous setup
without entering the folders again.

## What you need

You need Docker on a 64-bit NAS or computer, a working Emby or Jellyfin server, and a player that can open your movies
over the network. They must be able to communicate on your local network. The guide explains Docker, credentials, and
folders where needed; you do not need to edit HCC configuration files.

Follow [installation](INSTALL.en.md), then [first steps](docs/getting-started.en.md). If HCC is already installed, keep
the `home-cinema-control-config` volume and use the appropriate update guide.

## Help, privacy, and participation

Open **Diagnostics** when a connection or playback fails. [Troubleshooting](docs/troubleshoot.en.md) explains how to
share useful information and contact support. For HCC
bugs, [open a GitHub issue](https://github.com/tousled/home-cinema-control/issues/new); for installation questions,
email [support](mailto:llorente.software.solutions@gmail.com).

[Telemetry](docs/telemetry.en.md) is off by default and requires consent. [Take part](docs/participate.en.md) offers
short questions and suggestions without an account or email. Participation is optional and votes do not promise
implementation.

See the [Home Assistant guide](docs/home-assistant.en.md) to connect your own lighting or scene automations.
The [historical AVPasión tutorial](https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867)
provides background on NAS shares and OPPO preparation; use HCC's Docker instructions to install this application.

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
