# Release Policy

This document defines how Home Cinema Control is versioned, released, and upgraded.

## Versioning

- Versions follow `MAJOR.MINOR.PATCH` (no `v` prefix on tags — the release workflow matches `[0-9]*.[0-9]*.[0-9]*`).
- **`0.x` is pre-1.0.** Breaking changes to config shape, secrets layout, or behavior may still happen between minor
  versions, as already stated in `CHANGELOG.md`.
- **`0.9.x` is the 1.0.0 stabilization line.** Starting from the `0.9.0` tag, new work lands on `0.9.x` patch/minor
  releases for final hardening (bug fixes, polish, hardware validation) rather than directly on `1.0.0`. No new feature
  scope is added during this phase — see "1.0.0 readiness" below for what's actually gating the jump.
- **`1.0.0`** is the first release where config/secrets shape is considered stable across upgrades without a
  breaking-change note. The project is source-available, not open source; commercial distribution still requires an
  explicit licensing decision or written permission.
- Post-1.0.0, breaking changes to persisted config or secrets require a migration path in `config/migration.py`, not
  just a changelog note.

## Release artifacts

- **Docker images** are the only supported release artifact. There is no separate source tarball/zip release process.
- Images publish to two registries on every tag push matching `[0-9]*.[0-9]*.[0-9]*` (`.github/workflows/release.yml`):
    - `ghcr.io/tousled/home-cinema-control:<version>` and `:latest` (primary)
    - `tousled/home-cinema-control:<version>` and `:latest` (Docker Hub mirror)
- Both are multi-arch (`linux/amd64`, `linux/arm64`).
- `compose.yaml` pins the image via `${HCC_VERSION:-latest}` so a deployment can stay on a known-good tag instead of
  always tracking `latest`.

## Upgrade behavior (config & secrets)

- `/config` is a named Docker volume (`home-cinema-control-config`), independent of the image. Pulling a new image and
  recreating the container does **not** touch its contents — confirmed empirically across multiple rebuild/recreate
  cycles during the `bugfix/oppo_smb_playback` hardware validation session (2026-06-18).
- On startup, `config/migration.py` (`apply_all_migrations`) transforms any legacy flat-format `config.json` into the
  current nested-section shape in place. This is idempotent — re-running it against an already-migrated config is a
  no-op (`test_canonical_config_is_unchanged_by_migration`).
- **Known gap, by design, not a bug:** `migrate_secrets_from_config()` is a no-op. Legacy Emby username/password
  authentication (pre-token auth) is **not** carried forward. A user upgrading from a very old config that predates
  token-based Emby auth will need to reconnect Emby from the setup wizard. This has never been exercised against a real
  legacy `config.json`/`secrets.json` pair (none was available at the time of writing) — only against synthetic fixtures
  in `tests/test_config_migration.py`. Flagged here so it doesn't get rediscovered as a surprise.
- Secrets (`secrets.json`) are never overwritten by a partial config save — `save_effective_config` merges into the
  existing file rather than replacing it.

## Update UI semantics

The Status view's **Update** button is informational/trigger-only, never a direct upgrade executor:

- With a webhook URL configured (Watchtower/Coolify/Portainer Business), clicking **Update** POSTs to that webhook. The
  deployment platform — not HCC — pulls the image and restarts the container.
- Without a webhook, clicking **Update** shows the manual command (`docker compose pull && docker compose up -d`) for
  the user to run themselves.
- HCC never shells out to `docker` itself. This satisfies the "no silent automatic update" requirement without needing
  further UI changes.
- **Rollback** is symmetric: the previous version is recorded in `app.previous_version` before an update, and the Status
  view shows the exact `HCC_VERSION=<previous> docker compose pull && ... up -d` command to revert.

## License & contribution status — source-available

HCC uses the custom **Home Cinema Control Source Available License 1.0** in `LICENSE`:

- HCC should be released from a new repository without the historical Xnoppo commit graph. The public project should not
  be positioned as a continuation of the previous repository.
- Public attribution may state that HCC was inspired by the original Xnoppo idea by siberian-git and by AVPasion
  community knowledge. It should not state that HCC reuses Xnoppo implementation.
- The repository may be public, but HCC must not be described as open source.
- The license allows source inspection, evaluation, and personal non-commercial use.
- Commercial use, redistribution, hosted services, paid support bundles, published container images/packages, and sale
  of
  derivative works require written permission from the maintainer.
- External contributions are gated through `CONTRIBUTING.md`; code contributions should not be accepted casually without
  confirming the contributor has the right to submit and grants relicensing rights.

## 1.0.0 readiness

Cross-checked against the project's internal roadmap exit criteria and current state (2026-06-18):

| Criterion                                                             | Status                                                                                                                                        |
|-----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| Optional TV/AV control is safe and does not break playback            | ✅ Hardware-validated (acceptance matrix 3.1–3.4)                                                                                              |
| Media path setup can preview/test mappings and explain mount failures | ✅                                                                                                                                             |
| Startup failures produce structured diagnostics                       | ✅ (now also translated and log-level-aligned)                                                                                                 |
| MKV/ISO/BDMV/UHD playback acceptance matrix with hardware status      | ✅ Effectively complete (only 4.4 "OPPO play rejected" deliberately deferred — no safe way to reproduce without real codec/file-level failure) |
| Emby watched-device/library readiness is visible                      | ✅                                                                                                                                             |
| Stop/return/progress behavior verified                                | ✅ Hardware-validated this session                                                                                                             |
| Docker/NAS deployment docs and smoke checks exist                     | ✅                                                                                                                                             |
| OPPO/Chinoppo compatibility evidence recorded                         | ✅ Including real Chinoppo M9702 + `autoscript` validation (2026-06-18)                                                                        |
| **Release/update/license policy defined**                             | ✅ Source-available license and contribution gate added                                                                                        |

Everything else on the roadmap's P0/P1 backlog (`HCC-TASK-001` through `009`, `011`) is marked `done`. Remaining
pre-release work is release packaging/legal review, not feature work, Jellyfin/Samsung/multi-room (those are explicitly
out of scope for 1.0.0 per the roadmap's execution rules).
