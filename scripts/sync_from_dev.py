#!/usr/bin/env python3
"""Sync vendor WorldEngine, packer tools, and mod-template from sibling worldengine/."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEV = KIT_ROOT.parent / "worldengine"

# Only these root-level WorldEngine files are kept (plus the worldengine/ package).
WE_ROOT_KEEP_FILES = {
    "LICENSE.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "MANIFEST.in",
}

WE_EXCLUDE_DIR_NAMES = {
    "venv",
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".github",
    "worldengine.egg-info",
    "tests",
    "manual",
    "docs",
    "bin",
}

WE_EXCLUDE_SUFFIXES = {".world", ".png", ".pyc", ".pyo"}

WE_ALWAYS_KEEP_NAMES = {
    "LICENSE.txt",
    "LICENSE",
    "COPYING",
    "NOTICE",
    "NOTICE.txt",
}

# Runtime packer only (verify/inspect are optional and omitted from release sync).
PACKER_FILES = (
    "pack_vsplanet.py",
    "vsplanet.py",
    "World_pb2.py",
    "requirements.txt",
)


def _should_skip_we(path: Path, root: Path) -> bool:
    if path.is_file() and path.name in WE_ALWAYS_KEEP_NAMES:
        return False
    rel = path.relative_to(root)

    # Root-level file: allowlist only
    if len(rel.parts) == 1 and path.is_file():
        return path.name not in WE_ROOT_KEEP_FILES

    for part in rel.parts:
        if part in WE_EXCLUDE_DIR_NAMES:
            return True
        if part.endswith(".egg-info"):
            return True
    if path.is_file() and path.suffix.lower() in WE_EXCLUDE_SUFFIXES:
        return True
    return False


def sync_worldengine(dev_root: Path, dest: Path) -> None:
    src = dev_root / "worldengine-0.20.0"
    if not src.is_dir():
        raise SystemExit(f"Missing WorldEngine fork: {src}")

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    for path in src.rglob("*"):
        if _should_skip_we(path, src):
            continue
        rel = path.relative_to(src)
        out = dest / rel
        if path.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, out)

    print(f"Synced WorldEngine -> {dest}")


def sync_packer(dev_root: Path, dest: Path) -> None:
    src = dev_root / "tools"
    if not src.is_dir():
        raise SystemExit(f"Missing packer tools: {src}")

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    for name in PACKER_FILES:
        f = src / name
        if not f.is_file():
            print(f"WARNING: missing packer file {f}", file=sys.stderr)
            continue
        shutil.copy2(f, dest / name)

    print(f"Synced packer -> {dest}")


def sync_mod_template(dev_root: Path, dest: Path) -> None:
    src = dev_root / "dist" / "stage"
    if not src.is_dir():
        raise SystemExit(
            f"Missing mod stage at {src}. Build the worldengine mod first (compile.bat)."
        )
    if not (src / "worldengine.dll").is_file():
        raise SystemExit(f"Missing worldengine.dll in {src}")

    if dest.exists():
        shutil.rmtree(dest)

    def ignore(directory: str, names: list[str]) -> set[str]:
        skipped: set[str] = set()
        for name in names:
            p = Path(directory) / name
            if name.endswith(".vsplanet"):
                skipped.add(name)
            elif name == "__pycache__":
                skipped.add(name)
            elif p.is_file() and name.endswith((".world", ".png", ".pdb")):
                skipped.add(name)
        return skipped

    shutil.copytree(src, dest, ignore=ignore)

    planets = dest / "assets" / "worldengine" / "planets"
    planets.mkdir(parents=True, exist_ok=True)
    readme = planets / "README.txt"
    if not readme.is_file():
        readme.write_text(
            "Place packed planets here (*.vsplanet). PlanetKit writes them automatically.\n",
            encoding="utf-8",
        )

    print(f"Synced mod-template -> {dest} (excluded *.vsplanet)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dev-root",
        type=Path,
        default=DEFAULT_DEV,
        help=f"Sibling worldengine repo [default: {DEFAULT_DEV}]",
    )
    ap.add_argument("--skip-worldengine", action="store_true")
    ap.add_argument("--skip-packer", action="store_true")
    ap.add_argument("--skip-mod-template", action="store_true")
    args = ap.parse_args()

    dev = args.dev_root.resolve()
    if not dev.is_dir():
        raise SystemExit(f"Dev root not found: {dev}")

    if not args.skip_worldengine:
        sync_worldengine(dev, KIT_ROOT / "vendor" / "worldengine")
    if not args.skip_packer:
        sync_packer(dev, KIT_ROOT / "vendor" / "packer")
    if not args.skip_mod_template:
        sync_mod_template(dev, KIT_ROOT / "mod-template")

    print("Sync complete.")


if __name__ == "__main__":
    main()
