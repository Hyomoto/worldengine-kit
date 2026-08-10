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
    """Put vendored packer on sys.path; WorldEngine comes from the venv/frozen bundle."""
    root = root or kit_root()
    packer = root / "vendor" / "packer"
    s = str(packer)
    if packer.is_dir() and s not in sys.path:
        sys.path.insert(0, s)
    we = root / "vendor" / "worldengine"
    try:
        import worldengine  # noqa: F401
    except ImportError:
        ws = str(we)
        if we.is_dir() and ws not in sys.path:
            sys.path.insert(0, ws)
    return root
