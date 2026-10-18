# Release Policy

HCC uses semantic version tags without a `v` prefix.

- Stable releases use `MAJOR.MINOR.PATCH` tags.
- Prereleases use tags such as `MAJOR.MINOR.PATCH-rc.N`.
- Stable Docker images use a version tag and `latest`.
- Prerelease Docker images use a version tag and `rc`.
- The public repository is the source of release metadata consumed by the installed updater.
- Release notes preserve the original historical notes and identify the original publication date.

The build source and internal release automation are maintained privately. This public repository contains product documentation, release metadata, support information, and the public issue tracker; it does not contain HCC source code.
