# Release Policy

This document defines how Home Cinema Control is versioned, released, and upgraded.

## Versioning

- Versions follow `MAJOR.MINOR.PATCH` (no `v` prefix on tags — the release workflow matches `[0-9]*.[0-9]*.[0-9]*`).
- **`0.x` was the pre-1.0 stabilization period.** Breaking changes to config shape, secrets layout, or behavior were
  allowed there while the legacy bridge architecture was removed.
- **`1.0.0` is the first stable public release line.** From here, persisted config/secrets shape is considered stable
  across upgrades unless a migration path and changelog entry explicitly say otherwise. The project is source-available,
  not open source; commercial distribution still requires an explicit licensing decision or written permission.
- Post-1.0.0, breaking changes to persisted config or secrets require a migration path in `config/migration.py`, not
  just a changelog note.

## Branch and tag flow

- Feature, bugfix, refactor, docs, and chore branches merge into `develop`.
- `develop` is the integration branch and may be tagged with release candidates such as `1.0.0-rc.1`.
- `main` is the stable release branch. Stable tags such as `1.0.0`, `1.0.1`, or `1.1.0` must point to commits contained
  in `main`.
- Pull requests into `main` come only from `develop` or from `hotfix/*` branches, enforced by
  `.github/workflows/branch-policy.yml`.
- `hotfix/*` branches are cut from `main` (not `develop`), for fixes that can't wait for the next regular release.
  After merging a hotfix into `main` and tagging the patch release (e.g. `1.0.1`), open a second PR backporting the
  same hotfix branch into `develop` so the fix isn't lost or reintroduced as a regression in the next release.
- The release workflow validates tag placement:
    - tags containing `-` are treated as pre-releases and must be contained in `develop`;
    - plain `MAJOR.MINOR.PATCH` tags are stable releases and must be contained in `main`.
- `develop` and `main` are both branch-protected on GitHub (PR + passing status checks required, `enforce_admins`
  enabled). Nobody pushes a commit directly to either branch, including release-prep version bumps — those go through
  a `chore/release-<version>` branch and PR like any other change. Git tags are not protected, so `git push origin
  <tag>` after the merge remains a direct push.

## Release artifacts

- **Docker images** are the only supported release artifact. There is no separate source tarball/zip release process.
- Images publish to two registries on every matching tag push (`.github/workflows/release.yml`):
    - stable tag: `ghcr.io/tousled/home-cinema-control:<version>` and `:latest` (primary)
    - stable tag: `tousled/home-cinema-control:<version>` and `:latest` (Docker Hub mirror)
    - release candidate tag: `:<version>` and `:rc`, never `:latest`
- Both are multi-arch (`linux/amd64`, `linux/arm64`).
- `compose.yaml` pins the image via `${HCC_VERSION:-latest}` so a deployment can stay on a known-good tag instead of
  always tracking `latest`.
- Release images include OCI metadata labels for title, description, source, documentation, license, version, and
  revision.
- Docker Hub's public overview is maintained from `DOCKERHUB.md` by the release workflow, including the short
  description used on the repository listing.

## Docker Hub presentation

- `DOCKERHUB.md` is the source of truth for Docker Hub's **Overview** tab. Keep it concise, Docker-focused, and in
  English so registry visitors can understand the project before opening the full GitHub documentation.
- Images embedded in `DOCKERHUB.md` should use absolute `raw.githubusercontent.com` URLs because Docker Hub renders the
  overview outside GitHub's relative asset context.
- The release workflow updates Docker Hub with `peter-evans/dockerhub-description` after a successful multi-arch image
  push. This requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repository secrets.
- The synced short description must stay within Docker Hub's 100-character repository description limit.
- Visual settings that Docker Hub does not expose through the workflow, such as repository logo/avatar and category
  placement, remain manual Docker Hub settings.

Manual Docker Hub branding checklist:

- Use `assets/brand/hcc-mark.png` as the square avatar/logo candidate. It is already 512x512 PNG and works better than
  the horizontal wordmark in small Docker Hub icon slots.
- In a Community account, first try the account or namespace avatar settings in Docker Hub. Docker Hub has historically
  relied on profile/namespace avatar behavior for non-publisher accounts, and the result may take a while to propagate.
- If the repository page shows a camera/upload control over the repository icon, upload `assets/brand/hcc-mark.png`
  there. Docker documents that repository-logo upload flow for Trusted Content programs.
- If the repository page does not expose that camera/upload control, the per-repository logo is not available for the
  current account tier. In that case, the practical options are the namespace avatar plus the logo embedded in
  `DOCKERHUB.md`, or applying for Docker Verified Publisher / Docker-Sponsored Open Source if the project qualifies.

## Version source of truth

- The Git tag is the release source of truth. No file in the repo needs to be edited for a release to carry the right
  version.
- The Python package version is dynamic through `setuptools_scm`.
- The Docker release workflow passes `SETUPTOOLS_SCM_PRETEND_VERSION=<tag>` during image build, so the runtime version
  shown by the app matches the pushed tag even though `.git` is excluded from Docker context.
- The README version badge is a dynamic `img.shields.io/github/v/tag/...` badge that reads the latest tag directly
  from GitHub (sorted by semver) — it updates itself on tag push and needs no commit.
- `HCC_VERSION` in `compose.yaml` defaults to `latest`. To pin a deployment to a known-good tag, create a local
  `.env` (gitignored, never committed) with `HCC_VERSION=<version>`. This is a per-deployment choice, not something
  the release procedure produces or depends on.

## Release procedure

Release candidate:

```bash
git checkout develop && git pull
git tag 1.0.0-rc.1
git push origin 1.0.0-rc.1
```

Stable release (after the RC has been validated):

```bash
# open PR develop -> main, wait for checks, merge
git checkout main && git pull
git tag 1.0.0
git push origin 1.0.0
```

The PR merging `develop` into `main` is a regular merge commit (not squash/rebase) so `main`'s history stays a
superset of `develop`'s — squash or rebase merge must stay disabled for that PR direction in the repo's merge button
settings. The stable tag publishes `:<version>` and `:latest`. The RC tag publishes `:<version>` and `:rc`.

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
