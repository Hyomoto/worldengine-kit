"""Environment checks so install failures surface before Generate."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from importlib import import_module
from typing import Callable

from planetkit.paths import ensure_import_paths, kit_root, user_root

REQUIRED_MODULES: tuple[tuple[str, str], ...] = (
    ("numpy", "numpy"),
    ("google.protobuf", "protobuf"),
    ("PIL", "Pillow"),
    ("platec", "PyPlatec"),
    ("noise", "noise"),
    ("png", "pypng"),
    ("worldengine", "worldengine (vendor)"),
)

PACKER_MODULES: tuple[str, ...] = ("vsplanet", "pack_vsplanet")


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass
class DoctorResult:
    ok: bool
    checks: list[CheckResult] = field(default_factory=list)
    missing_modules: list[str] = field(default_factory=list)

    @property
    def lines(self) -> list[str]:
        out: list[str] = []
        for c in self.checks:
            mark = "OK" if c.ok else "FAIL"
            out.append(f"[{mark}] {c.name}: {c.detail}")
        return out


def _check_python_version() -> CheckResult:
    major, minor = sys.version_info[:2]
    ver = f"{major}.{minor}.{sys.version_info[2]}"
    if (major, minor) < (3, 9):
        return CheckResult("python_version", False, f"{ver} (need Python 3.9+)")
    return CheckResult("python_version", True, f"{ver} ({sys.version.split()[0]})")


def _check_executable() -> CheckResult:
    exe = sys.executable or "(unknown)"
    frozen = getattr(sys, "frozen", False)
    lower = exe.lower().replace("\\", "/")
    warnings: list[str] = []
    if frozen:
        warnings.append("frozen=True")
    # Windows Store / stub installs often break venvs and pip wheels.
    if "windowsapps" in lower or "microsoft/windowsapps" in lower:
        warnings.append("Windows Store Python stub detected — install python.org Python and re-run setup.bat")
    detail = exe if not warnings else f"{exe} ({'; '.join(warnings)})"
    ok = "Windows Store Python stub" not in detail
    return CheckResult("python_executable", ok, detail)


def _try_import(module: str) -> tuple[bool, str]:
    try:
        mod = import_module(module)
        ver = getattr(mod, "__version__", None)
        if ver is not None:
            return True, f"import ok (version {ver})"
        loc = getattr(mod, "__file__", None)
        if loc:
            return True, f"import ok ({loc})"
        return True, "import ok"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _check_modules() -> tuple[list[CheckResult], list[str]]:
    checks: list[CheckResult] = []
    missing: list[str] = []
    for module, label in REQUIRED_MODULES:
        ok, detail = _try_import(module)
        checks.append(CheckResult(f"import:{module}", ok, detail if ok else f"{detail} - pip package '{label}'"))
        if not ok:
            missing.append(module)
    return checks, missing


def _check_packer() -> tuple[list[CheckResult], list[str]]:
    ensure_import_paths()
    checks: list[CheckResult] = []
    missing: list[str] = []
    for module in PACKER_MODULES:
        ok, detail = _try_import(module)
        checks.append(CheckResult(f"import:{module}", ok, detail))
        if not ok:
            missing.append(module)
    return checks, missing


def _check_layout() -> list[CheckResult]:
    root = kit_root()
    checks: list[CheckResult] = []
    entries: list[tuple[str, Path, str]] = [
        ("vendor/worldengine", root / "vendor" / "worldengine", "dir"),
        ("vendor/packer", root / "vendor" / "packer", "dir"),
        ("mod-template/worldengine.dll", root / "mod-template" / "worldengine.dll", "file"),
    ]
    if not getattr(sys, "frozen", False):
        entries.append(
            (
                "vendor/worldengine/pyproject.toml",
                root / "vendor" / "worldengine" / "pyproject.toml",
                "file",
            )
        )

    for label, path, kind in entries:
        exists = path.is_dir() if kind == "dir" else path.is_file()
        checks.append(
            CheckResult(
                f"layout:{label}",
                exists,
                str(path) if exists else f"missing: {path}",
            )
        )
    return checks


def run_doctor() -> DoctorResult:
    checks: list[CheckResult] = []
    missing: list[str] = []

    checks.append(_check_python_version())
    checks.append(_check_executable())

    mod_checks, mod_missing = _check_modules()
    checks.extend(mod_checks)
    missing.extend(mod_missing)

    pack_checks, pack_missing = _check_packer()
    checks.extend(pack_checks)
    missing.extend(pack_missing)

    checks.extend(_check_layout())

    ok = all(c.ok for c in checks)
    return DoctorResult(ok=ok, checks=checks, missing_modules=missing)


def format_report(result: DoctorResult) -> str:
    lines = [
        "=== PlanetKit environment report (copy/paste for bug reports) ===",
        f"platform: {platform.platform()}",
        f"python: {sys.version.replace(chr(10), ' ')}",
        f"executable: {sys.executable}",
        f"frozen: {getattr(sys, 'frozen', False)}",
        f"kit_root: {kit_root()}",
        f"user_root: {user_root()}",
        f"overall: {'OK' if result.ok else 'FAILED'}",
    ]
    if result.missing_modules:
        lines.append("missing_modules: " + ", ".join(result.missing_modules))
    else:
        lines.append("missing_modules: (none)")
    lines.append("--- checks ---")
    lines.extend(result.lines)
    lines.append("=== end report ===")
    if not result.ok:
        lines.append("Fix: close PlanetKit, re-run setup.bat, then PlanetKit.bat.")
        lines.append("If setup.bat reported pip errors, install Python 3.9+ from python.org with PATH enabled.")
    return "\n".join(lines)


def ensure_ready(*, stream: Callable[[str], None] | None = None, exit_on_fail: bool = False) -> DoctorResult:
    """Run doctor; optionally print and/or SystemExit(1)."""
    result = run_doctor()
    report = format_report(result)
    if stream:
        stream(report)
    else:
        print(report)
    if not result.ok and exit_on_fail:
        raise SystemExit(1)
    return result


def main(argv: list[str] | None = None) -> int:
    _ = argv  # unused; kept for CLI symmetry
    result = run_doctor()
    print(format_report(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
