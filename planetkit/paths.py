"""Resolve kit root for source and frozen (PyInstaller) layouts."""

from __future__ import annotations

import sys
from pathlib import Path


def user_root() -> Path:
    """Writable location for output/ and planet.json (beside the exe when frozen)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def kit_root() -> Path:
    """Read-only kit data: presets, vendor, mod-template, docs."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = Path(meipass)
            if (candidate / "presets").is_dir() or (candidate / "mod-template").is_dir():
                return candidate
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "presets").is_dir():
            return exe_dir
        return exe_dir
    return Path(__file__).resolve().parents[1]


def ensure_import_paths(root: Path | None = None) -> Path:
    """Prefer vendored WorldEngine/packer so PlanetKit patches always win over site-packages."""
    root = root or kit_root()
    for rel in ("vendor/worldengine", "vendor/packer"):
        path = root / Path(rel)
        s = str(path)
        if path.is_dir() and s not in sys.path:
            sys.path.insert(0, s)
    return root
