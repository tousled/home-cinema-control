#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-rc\.\d+)?$")


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text()
    next_text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"Could not update {path}: pattern not found")
    path.write_text(next_text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare local release metadata. The Git tag remains the release source of truth.",
    )
    parser.add_argument("version", help="Version such as 1.0.0 or 1.0.0-rc.1")
    args = parser.parse_args()

    version = args.version.strip()
    if not VERSION_RE.fullmatch(version):
        raise SystemExit("Version must match MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH-rc.N")

    replace_once(PROJECT_ROOT / ".env", r"^HCC_VERSION=.*$", f"HCC_VERSION={version}")
    badge = f"https://img.shields.io/badge/version-{version}-gold"
    for readme in ("README.md", "README.en.md"):
        replace_once(
            PROJECT_ROOT / readme,
            r"https://img\.shields\.io/badge/version-[^-\"/]+(?:-rc\.\d+)?-gold",
            badge,
        )

    print(f"Prepared local release metadata for {version}")
    print("Create the Git tag with the same version to publish the Docker image.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
