"""Assemble a playable mod zip from mod-template + packed planet."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Callable

from planetkit.paths import kit_root
from planetkit.schema import PlanetConfig

LogFn = Callable[[str], None]


def _log(msg: str, log: LogFn | None) -> None:
    if log:
        log(msg)
    else:
        print(msg)


def assemble_mod(
    cfg: PlanetConfig,
    planet_path: Path,
    work_dir: Path,
    *,
    template_dir: Path | None = None,
    log: LogFn | None = None,
) -> Path:
    """Copy template, inject planet + config, return path to zip."""
    template_dir = template_dir or (kit_root() / "mod-template")
    if not template_dir.is_dir():
        raise FileNotFoundError(
            f"mod-template missing at {template_dir}. Run scripts/sync_from_dev.py after building the mod."
        )
    if not (template_dir / "worldengine.dll").is_file():
        raise FileNotFoundError(f"worldengine.dll missing in {template_dir}")
    if not planet_path.is_file():
        raise FileNotFoundError(f"Planet not found: {planet_path}")

    mod_dir = work_dir / f"{cfg.name}-mod"
    if mod_dir.exists():
        shutil.rmtree(mod_dir)
    shutil.copytree(template_dir, mod_dir)

    planet_name = cfg.planet_asset_name()
    planets_dir = mod_dir / "assets" / "worldengine" / "planets"
    planets_dir.mkdir(parents=True, exist_ok=True)
    # Remove any leftover sample planets from a partial template
    for old in planets_dir.glob("*.vsplanet"):
        old.unlink()
    dest_planet = planets_dir / planet_name
    shutil.copy2(planet_path, dest_planet)
    _log(f"Injected planet -> {dest_planet}", log)

    config_path = mod_dir / "assets" / "worldengine" / "config" / "worldengine.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.is_file():
        with config_path.open(encoding="utf-8") as f:
            runtime = json.load(f)
    else:
        runtime = {}
    if not isinstance(runtime, dict):
        runtime = {}

    runtime["planetAssetPath"] = f"worldengine:planets/{planet_name}"
    runtime["tempMinC"] = float(cfg.tempMinC)
    runtime["tempMaxC"] = float(cfg.tempMaxC)
    runtime["enabled"] = True

    with config_path.open("w", encoding="utf-8") as f:
        json.dump(runtime, f, indent=2)
        f.write("\n")
    _log(f"Wrote runtime config -> {config_path}", log)
    _log(
        f"Note: VS ModConfig/worldengine.json overlays asset defaults. "
        f"Planet is installed as '{planet_name}' (path worldengine:planets/{planet_name}). "
        f"If load fails with planet not found, check ModConfig PlanetAssetPath matches.",
        log,
    )

    zip_path = work_dir.parent / f"{cfg.name}-worldengine.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in mod_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(mod_dir).as_posix())
    _log(f"Wrote mod zip -> {zip_path}", log)
    return zip_path
