#!/usr/bin/env python3
"""Remove build/runtime junk from worldengine-kit (venv, dist, caches, outputs)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]

DIR_TARGETS = (
    "venv",
    ".venv",
    "dist",
    "build",
    "output",
    "worldengine_planet_kit.egg-info",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
)

NAME_TARGETS = {
    "__pycache__",
    "*.egg-info",
}


def _rm(path: Path, *, dry_run: bool) -> int:
    if not path.exists():
        return 0
    size = 0
    if path.is_file():
        size = path.stat().st_size
        print(f"  file {path.relative_to(KIT_ROOT)}")
        if not dry_run:
            path.unlink()
    else:
        for f in path.rglob("*"):
            if f.is_file():
                size += f.stat().st_size
        print(f"  dir  {path.relative_to(KIT_ROOT)} ({size / (1024 * 1024):.1f} MB)")
        if not dry_run:
            shutil.rmtree(path, ignore_errors=True)
    return size


def clean(*, dry_run: bool, deep_vendor: bool) -> int:
    print(f"Cleaning {'(dry-run) ' if dry_run else ''}{KIT_ROOT}")
    total = 0
    for name in DIR_TARGETS:
        total += _rm(KIT_ROOT / name, dry_run=dry_run)

    # Nested caches / egg-info anywhere under kit (except we may leave vendor source)
    for path in KIT_ROOT.rglob("__pycache__"):
        if path.is_dir():
            total += _rm(path, dry_run=dry_run)
    for path in KIT_ROOT.rglob("*.egg-info"):
        if path.is_dir():
            total += _rm(path, dry_run=dry_run)
    for path in KIT_ROOT.rglob("*.pyc"):
        if path.is_file():
            total += _rm(path, dry_run=dry_run)

    # User/local noise
    for name in ("planet.json.bak",):
        total += _rm(KIT_ROOT / name, dry_run=dry_run)

    if deep_vendor:
        # Dev-only WorldEngine tree fluff if present after a loose sync
        vendor = KIT_ROOT / "vendor" / "worldengine"
        for name in (
            "uv.lock",
            "Dockerfile",
            "tox.ini",
            "setup_venv.sh",
            "run.bat",
            "biomes.scm",
            ".pre-commit-config.yaml",
            ".python-version",
            ".gitignore",
            "CHANGELOG.md",
            "README.md",
        ):
            total += _rm(vendor / name, dry_run=dry_run)

    print(f"Removed ~{total / (1024 * 1024):.1f} MB")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--deep-vendor",
        action="store_true",
        help="Also delete known non-runtime files under vendor/worldengine",
    )
    args = ap.parse_args()
    return clean(dry_run=args.dry_run, deep_vendor=args.deep_vendor)


if __name__ == "__main__":
    raise SystemExit(main())
