#!/usr/bin/env python3
"""Build a lean release zip of worldengine-kit (no venv/dist/build/output)."""

from __future__ import annotations

import argparse
import zipfile
from datetime import datetime, timezone
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]

# Paths relative to kit root included in the release zip.
INCLUDE_FILES = (
    "README.md",
    "QUICKSTART.md",
    "THIRD_PARTY.md",
    "setup.bat",
    "PlanetKit.bat",
    "clean.bat",
    "requirements.txt",
    "pyproject.toml",
    "planetkit_app.py",
    "PlanetKit.spec",
)

INCLUDE_DIRS = (
    "planetkit",
    "presets",
    "docs",
    "licenses",
    "vendor",
    "mod-template",
    "scripts",
)

SKIP_DIR_NAMES = {
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "dist",
    "build",
    "output",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

SKIP_SUFFIXES = {".pyc", ".pyo", ".vsplanet", ".world", ".png"}

SKIP_FILE_NAMES = {
    "uv.lock",
    "Dockerfile",
    "tox.ini",
    "setup_venv.sh",
    "run.bat",
    "biomes.scm",
    ".pre-commit-config.yaml",
    ".python-version",
    "planet.json",  # machine-local last-used config
    "pack_release.py",  # maintainer-only; not for end-user kits
    "pack_release.bat",
}


def _skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIR_NAMES or part.endswith(".egg-info"):
            return True
    if path.name in SKIP_FILE_NAMES:
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    return False


def iter_release_files() -> list[Path]:
    files: list[Path] = []
    for name in INCLUDE_FILES:
        p = KIT_ROOT / name
        if p.is_file():
            files.append(p)
    for dirname in INCLUDE_DIRS:
        root = KIT_ROOT / dirname
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and not _skip(path.relative_to(KIT_ROOT)):
                files.append(path)
    return sorted(files)


def pack(out: Path) -> Path:
    files = iter_release_files()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            arc = Path("worldengine-kit") / path.relative_to(KIT_ROOT)
            zf.write(path, arc.as_posix())
    bytes_ = out.stat().st_size
    print(f"Wrote {out} ({bytes_ / (1024 * 1024):.2f} MB, {len(files)} files)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output zip path (default: release/worldengine-kit-YYYYMMDD.zip)",
    )
    ap.add_argument("--list", action="store_true", help="List files that would be packed")
    args = ap.parse_args()

    if args.list:
        for p in iter_release_files():
            print(p.relative_to(KIT_ROOT).as_posix())
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out = args.output or (KIT_ROOT / "release" / f"worldengine-kit-{stamp}.zip")
    pack(out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
