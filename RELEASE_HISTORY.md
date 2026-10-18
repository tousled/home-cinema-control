# HCC release history

This document preserves the documented evolution of Home Cinema Control from `0.1.0` onward. The public repository was reconstructed as a documentation and distribution repository when product development moved to a private source repository; it is not a new beginning for the project.

Dates below preserve the source records rather than forcing one date system to
match another. CHANGELOG dates, tag dates, and GitHub Release `published_at`
dates can differ; when they do, both dates are preserved in the specific
release record and its migration manifest. A version is marked `changelog-only`
when it is documented in the historical changelog but has no matching
historical tag or GitHub Release. A `tagged` version has a historical tag but no
GitHub Release. `GitHub Release` identifies a version with a historical release;
prereleases and release candidates are listed separately.

The CHANGELOG genuinely contains two `0.8.0` entries, dated `2026-06-11` and
`2026-06-13`. Both entries are retained because they are separate historical
records; this is not a migration-generated duplicate.

## Documented versions

| Version | Original date | Historical status | Recorded change summary |
| --- | --- | --- | --- |
| `0.1.0` | 2026-05-22 | `changelog-only` | Established the clean baseline for the project. |
| `0.1.1` | 2026-05-22 | `changelog-only` | Sanitized runtime debug logs to avoid exposing sensitive values during troubleshooting. |
| `0.2.0` | 2026-05-22 | `changelog-only` | Added Docker runtime support. |
| `0.3.0` | 2026-05-23 | `changelog-only` | Added OPPO QPL diagnostics for playback-state observation. |
| `0.4.0` | 2026-05-23 | `changelog-only` | Added Python 3.14 runtime support. |
| `0.5.0` | 2026-05-31 | `changelog-only` | Added a parent playback orchestrator that coordinates startup, post-start |
| `0.5.1` | 2026-06-01 | `changelog-only` | Updated the web-reported application version to `0.5.1`. |
| `0.6.0` | 2026-06-06 | `changelog-only` | Added OPPO verbose event bridge (`oppo.observation_mode = "oppo_verbose"`) as |
| `0.6.1` | 2026-06-06 | `changelog-only` | Fixed Docker container producing no output in `docker logs` and Portainer log |
| `0.7.0` | 2026-06-09 | `changelog-only` | Added OPPO SVM 3 verbose mode with UTC position stream as the new default |
| `0.7.1` | 2026-06-09 | `changelog-only` | Added deferred audio track selection for Blu-ray ISO/full-disc content. When |
| `0.7.2` | 2026-06-09 | `changelog-only` | Added Python package metadata for `home-cinema-control` using |
| `0.8.0` | 2026-06-11 | `changelog-only` | Added a new web application built with Vue 3 and FastAPI, replacing the |
| `0.8.0` | 2026-06-13 | `changelog-only` | Added hardware compatibility reference — validated player models, media formats, |
| `0.8.1` | 2026-06-13 | `changelog-only` | Added an **Update** button to the Status view. When a new version is detected, the button triggers an automated |
| `0.9.0` | 2026-06-18 | `changelog-only` | Added Spanish/English translations for all structured playback diagnostics |
| `0.9.1` | 2026-06-18 | `changelog-only` | Added a "Current playback" info panel next to the OPPO remote, showing |
| `1.0.0` | 2026-06-19 | `tagged` | Added the 1.0.0 release branch policy: release candidates are tagged from `develop`, stable releases are tagged from |
| `1.0.2` | 2026-06-20 | `tagged` | Fixed Emby authorization persistence so generated access tokens are kept in the private secrets file instead of being |
| `1.0.3` | 2026-06-21 | `tagged` | Fixed the OPPO folder browser ("Browse OPPO") failing with a connection error on a cold player, by activating the |
| `1.0.4` | 2026-06-21 | `tagged` | Fixed full Blu-ray / ISO playbacks not being marked as watched in the media server and the disc not stopping when |
| `1.0.5` | 2026-06-22 | `tagged` | Fixed Autoscript attempting to unmount NFS-mounted shares after playback finish; the Autoscript telnet-shell |
| `1.1.0` | 2026-06-26 | `GitHub Release` | Path mappings, detected libraries, the library-filter preference, and the monitored device now persist |
| `1.1.1` | 2026-06-27 | `GitHub Release` | Release tag pushes now create a GitHub Release automatically after the Docker image publishes, with release notes |
| `1.1.2` | 2026-06-27 | `GitHub Release` | Fixed the Logs and Diagnostics copy buttons for browsers that block or hide the Clipboard API. Copying the visible |
| `1.1.3` | 2026-06-29 | `GitHub Release` | Added opt-in product telemetry and roadmap feedback controls on the Diagnostics screen. Telemetry is disabled by |
| `1.1.4` | 2026-06-30 | `GitHub Release` | Fixed OPPO entering an unresponsive state after SMB playback when the autoscript Telnet shell was unavailable |
| `1.2.0` | 2026-07-07 | `GitHub Release` | Added a "Send diagnostics" action on the Diagnostics screen for reporting bugs from non-technical installs. It |
| `1.2.1` | 2026-07-08 | `GitHub Release` | Reduced OPPO natural-end detection tolerance so HCC no longer treats playback as finished ten seconds before the |
| `1.3.0` | 2026-08-13 | `GitHub Release` | Added native Trinnov Altitude AV receiver support over the Altitude TCP automation protocol. HCC identifies as |
| `1.3.1` | 2026-09-17 | `GitHub Release` | Bounded OPPO audio and subtitle menu polling by each configured phase timeout and added exponential backoff between |
| `1.3.2` | 2026-10-09 | `GitHub Release` | Normalized media path mappings at the prefix boundary so Linux and Windows source paths produce exactly one |
| `1.3.3` | 2026-10-09 | `GitHub Release` | Fixed direct Emby playback for STRM-backed items. HCC now preserves the physical `.strm` path for path mapping |
| `1.4.0` | 2026-10-12 | `GitHub Release` | HCC 1.4.0 connects playback events to Home Assistant and improves the visibility and reliability of playback startup and |
| `1.4.1` | 2026-10-17 | `GitHub Release` | HCC 1.4.1 improves playback reliability and diagnostics, media-track selection, Home Assistant integration, and OPPO |

## Prereleases and release candidates

These releases had a GitHub Release but do not have a matching version heading in the historical CHANGELOG. Their complete original notes are preserved in [`docs/releases/`](docs/releases/).

| Tag | Original date | Channel | Original tag commit |
| --- | --- | --- | --- |
| `1.1.1-rc.1` | 2026-06-27 | `prerelease` | `8bb551707bb480de684ad578283a002b20d715d3` |
| `1.1.1-rc.2` | 2026-06-27 | `prerelease` | `c2db654d7e9a35428b541b9a01ec3791a18f5e5b` |
| `1.1.1-rc.3` | 2026-06-27 | `prerelease` | `353c0259fd306777ecf4eaf1cec4445b1567c359` |
| `1.1.3-rc.1` | 2026-06-28 | `prerelease` | `7c2594e5b18faff0fcd3c0dd417a1cc0671ab67b` |
| `1.1.3-rc.2` | 2026-06-29 | `prerelease` | `3e0969eadaa0bfdb846148b012a231f8ff5f1995` |
| `1.2.0-rc.1` | 2026-07-01 | `prerelease` | `c7c1288b5f77c0e7a161172b2ada1f6f957ac387` |
| `1.2.0-rc.2` | 2026-07-02 | `prerelease` | `31db538379fe1eb31b6047aa5ef91ef599fe6de0` |
| `1.2.0-rc.3` | 2026-07-02 | `prerelease` | `5df6df1fddae94f8268b76f7ae5fe3816477fb97` |
| `1.2.0-rc.4` | 2026-07-02 | `prerelease` | `a3c7c1b39af6c0f7dfc4f4b62629dc36a00d8638` |
| `1.2.0-rc.5` | 2026-07-02 | `prerelease` | `7a5b0b1139815fa289c240b7e2a118ca376a6e2f` |
| `1.2.0-rc.6` | 2026-07-03 | `prerelease` | `8553e1f7deea9931fdf35d91ed6a44783a14c9f0` |
| `1.3.0-rc.1` | 2026-07-12 | `prerelease` | `7ddb1e10be37343de029953bb02ccbdb3182c4de` |
| `1.3.0-rc.2` | 2026-07-12 | `prerelease` | `81eabfcdcedfb183cf1967f45b48d66fdf72d5dc` |
| `1.4.0-rc.1` | 2026-10-12 | `prerelease` | `05812305afe73c45d037a4401f267f3cb9ea1d98` |
| `1.4.0-rc.2` | 2026-10-12 | `prerelease` | `5c482e596774ad8e71a8efa03d2fa30d8d498a2b` |
| `1.4.1-rc.1` | 2026-10-14 | `prerelease` | `eb04ef0381fe9f0211ccbf01cfea950a64728574` |
| `1.4.1-rc.2` | 2026-10-15 | `prerelease` | `aa9917fba26f9601fffbe9f939b8a1d9571f7256` |
| `1.4.1-rc.3` | 2026-10-16 | `prerelease` | `260b7c9d940d4a4492d4f311f1fa0a295f5cf6a7` |

## Historical tag inventory

The SHA values in this table are metadata from the historical repository only. They are not reused as Git objects in this repository. No historical tags have been created here yet.

| Tag | Original date | Type | Original commit SHA | GitHub Release |
| --- | --- | --- | --- | --- |
| `1.0.0` | 2026-06-19 | `lightweight` | `3ec6bcd27a321481485eada2e698f174d8e55fde` | no |
| `1.0.0-rc.1` | 2026-06-19 | `lightweight` | `35634cd7c201d7234112a6dc2cfbf7716285fbf3` | no |
| `1.0.1` | 2026-06-19 | `lightweight` | `0048548472b02e7172113dc75eafd4ddb7d24b3d` | no |
| `1.0.2` | 2026-06-20 | `lightweight` | `207519ad1ba035f0359456561ae21483c80736a7` | no |
| `1.0.3` | 2026-06-21 | `lightweight` | `a7d56847b9432d8f95142aca4c3a12dbe95a9bea` | no |
| `1.0.4` | 2026-06-21 | `lightweight` | `0290ad3637bc6c7a4f80fd83accdc7b81df62deb` | no |
| `1.0.5` | 2026-06-22 | `lightweight` | `8534dfb6698adc53a8c8f226d8fe70f03ef2697c` | no |
| `1.1.0-rc.1` | 2026-06-25 | `lightweight` | `98d60fdcaad7213a4eeae6fcec88c408a6bae809` | no |
| `1.1.0-rc.2` | 2026-06-25 | `lightweight` | `5d5753e943889b914adec0148dfd0e4462e856a5` | no |
| `1.1.0-rc.3` | 2026-06-25 | `lightweight` | `e3acd0b4c473a90728b8d73ee05f149287efd33c` | no |
| `1.1.0-rc.4` | 2026-06-25 | `lightweight` | `6e3627c0f4378d329bb4ab7bd436e651bae4d39e` | no |
| `1.1.0` | 2026-06-26 | `lightweight` | `e6b40dc6c8ab8061975e14adac387c8b803ae130` | yes |
| `1.1.0-rc.5` | 2026-06-26 | `lightweight` | `b669553085a7b63764095fd2ee9c4bbb4cb93885` | no |
| `1.1.1` | 2026-06-27 | `lightweight` | `68eaa7a6f19c2d13d3496b5de4ff5f2a0fb495c1` | yes |
| `1.1.1-rc.1` | 2026-06-27 | `lightweight` | `8bb551707bb480de684ad578283a002b20d715d3` | yes |
| `1.1.1-rc.2` | 2026-06-27 | `lightweight` | `c2db654d7e9a35428b541b9a01ec3791a18f5e5b` | yes |
| `1.1.1-rc.3` | 2026-06-27 | `lightweight` | `353c0259fd306777ecf4eaf1cec4445b1567c359` | yes |
| `1.1.2` | 2026-06-27 | `lightweight` | `c91c492153848e8291ffa1c20e13afa72ec19a54` | yes |
| `1.1.3` | 2026-06-29 | `lightweight` | `314aed91f2d49355915fb5df4c01efd52a7def5a` | yes |
| `1.1.3-rc.1` | 2026-06-29 | `lightweight` | `7c2594e5b18faff0fcd3c0dd417a1cc0671ab67b` | yes |
| `1.1.3-rc.2` | 2026-06-29 | `lightweight` | `3e0969eadaa0bfdb846148b012a231f8ff5f1995` | yes |
| `1.1.4` | 2026-06-30 | `lightweight` | `fbf9245e74c5bc661ec35bfdeb90e2da19cabed5` | yes |
| `1.2.0-rc.1` | 2026-07-01 | `lightweight` | `c7c1288b5f77c0e7a161172b2ada1f6f957ac387` | yes |
| `1.2.0-rc.2` | 2026-07-02 | `lightweight` | `31db538379fe1eb31b6047aa5ef91ef599fe6de0` | yes |
| `1.2.0-rc.3` | 2026-07-02 | `lightweight` | `5df6df1fddae94f8268b76f7ae5fe3816477fb97` | yes |
| `1.2.0-rc.4` | 2026-07-02 | `lightweight` | `a3c7c1b39af6c0f7dfc4f4b62629dc36a00d8638` | yes |
| `1.2.0-rc.5` | 2026-07-02 | `lightweight` | `7a5b0b1139815fa289c240b7e2a118ca376a6e2f` | yes |
| `1.2.0-rc.6` | 2026-07-04 | `lightweight` | `8553e1f7deea9931fdf35d91ed6a44783a14c9f0` | yes |
| `1.2.0` | 2026-07-07 | `lightweight` | `0e82b5c7e0bdb696b9eb4809649e4540521dd07b` | yes |
| `1.2.1` | 2026-07-08 | `lightweight` | `241f7abc27c780f5a3bdbbd8a597319e3957b11c` | yes |
| `1.3.0-rc.1` | 2026-07-12 | `lightweight` | `7ddb1e10be37343de029953bb02ccbdb3182c4de` | yes |
| `1.3.0-rc.2` | 2026-07-12 | `lightweight` | `81eabfcdcedfb183cf1967f45b48d66fdf72d5dc` | yes |
| `1.3.0` | 2026-08-13 | `lightweight` | `bc85b94caafff74137edc1c275c32bf9dfa4d245` | yes |
| `1.3.1` | 2026-09-17 | `lightweight` | `c31428c5c0cd2f8805e3f0e2c33f1db4ffdac8e5` | yes |
| `1.3.2` | 2026-10-09 | `lightweight` | `c11d2d05fdb0b7968ce6fd20f52aecc91dfc238c` | yes |
| `1.3.3` | 2026-10-09 | `lightweight` | `47e727993c40d3d63337499c0d439e7878f08a84` | yes |
| `1.4.0` | 2026-10-12 | `lightweight` | `7f59651c384834c9accc814ef1f3a218abb3d757` | yes |
| `1.4.0-rc.1` | 2026-10-12 | `lightweight` | `05812305afe73c45d037a4401f267f3cb9ea1d98` | yes |
| `1.4.0-rc.2` | 2026-10-12 | `lightweight` | `5c482e596774ad8e71a8efa03d2fa30d8d498a2b` | yes |
| `1.4.1-rc.1` | 2026-10-14 | `lightweight` | `eb04ef0381fe9f0211ccbf01cfea950a64728574` | yes |
| `1.4.1-rc.2` | 2026-10-15 | `lightweight` | `aa9917fba26f9601fffbe9f939b8a1d9571f7256` | yes |
| `1.4.1-rc.3` | 2026-10-16 | `lightweight` | `260b7c9d940d4a4492d4f311f1fa0a295f5cf6a7` | yes |
| `1.4.1-rc.4` | 2026-10-16 | `lightweight` | `260b7c9d940d4a4492d4f311f1fa0a295f5cf6a7` | no |
| `1.4.1` | 2026-10-17 | `lightweight` | `302548552d8e637107fb5eccabf39ebd9fa99dbf` | yes |

## Source records

The public release pages retain the original names, channels, dates, and release notes for all 31 historical GitHub Releases. Tags without a release are represented by the tag inventory and by the corresponding documented CHANGELOG entry when one exists. Historical release and issue URLs will be updated only after the later issue migration and release recreation steps are approved.
