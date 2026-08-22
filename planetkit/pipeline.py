"""End-to-end planet generation pipeline."""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path
from typing import Callable

from planetkit.assemble import assemble_mod
from planetkit.paths import ensure_import_paths, user_root
from planetkit.schema import PlanetConfig, apply_climate_extremes, save_config

LogFn = Callable[[str], None]

DEFAULT_TEMPS = [0.874, 0.765, 0.594, 0.439, 0.366, 0.124]
DEFAULT_HUMIDS = [0.941, 0.778, 0.507, 0.236, 0.073, 0.014, 0.002]


class _LogStream(io.TextIOBase):
    """
    Redirect stdout writes to the GUI to avoid locking up the main thread.
    """

    encoding = "utf-8"
    errors = "replace"

    def __init__(self, log: LogFn):
        super().__init__()
        self._log = log
        self._buf = ""

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip("\r")
            if line:
                self._log(line)
        return len(s)

    def flush(self) -> None:
        leftover = self._buf.rstrip("\r\n")
        self._buf = ""
        if leftover:
            self._log(leftover)


def _emit(msg: str, log: LogFn | None) -> None:
    if log:
        log(msg)
    else:
        print(msg)


def resolve_output_dir(cfg: PlanetConfig, root: Path | None = None) -> Path:
    root = root or user_root()
    out = Path(cfg.outputDir)
    if not out.is_absolute():
        out = root / out
    return out / cfg.name


def generate_world_files(cfg: PlanetConfig, work_dir: Path, *, log: LogFn | None = None) -> Path:
    ensure_import_paths()
    from worldengine.cli.main import generate_grayscale_heightmap, generate_world
    from worldengine.common import set_verbose
    from worldengine.step import Step

    work_dir.mkdir(parents=True, exist_ok=True)
    set_verbose(bool(cfg.verbose))
    step = Step.get_by_name("full")

    _emit(
        f"Generating world '{cfg.name}' {cfg.width}x{cfg.height} seed={cfg.seed} plates={cfg.numberOfPlates} ...",
        log,
    )

    out_stream: io.TextIOBase = _LogStream(log) if log else sys.stdout  # type: ignore[assignment]
    with contextlib.redirect_stdout(out_stream):
        world = generate_world(
            cfg.name,
            cfg.width,
            cfg.height,
            cfg.seed,
            cfg.numberOfPlates,
            str(work_dir).replace("\\", "/"),
            step,
            cfg.oceanLevel,
            list(DEFAULT_TEMPS),
            list(DEFAULT_HUMIDS),
            world_format="protobuf",
            fade_borders=True,
            verbose=bool(cfg.verbose),
            gamma_curve=float(cfg.precipGamma),
            curve_offset=float(cfg.precipGammaOffset),
            distance_to_sun=float(cfg.distanceToSun),
            axial_tilt=float(cfg.axialTilt),
            folding_ratio=cfg.foldingRatio,
            plate_erosion_period=cfg.plateErosionPeriod,
            cycle_count=cfg.cycleCount,
            elev_noise_octaves=cfg.elevNoiseOctaves,
            elev_noise_amp=cfg.elevNoiseAmp,
            elev_blur_steps=cfg.elevBlurSteps,
            shelf_radius=cfg.shelfRadius,
            shelf_shallow=cfg.shelfShallow,
            shelf_break=cfg.shelfBreak,
            noisy_coastlines=cfg.noisyCoastlines,
            shelf_width_noise=cfg.shelfWidthNoise,
            shelf_depth_noise=cfg.shelfDepthNoise,
            shelf_ocean_depth=cfg.shelfOceanDepth,
            shelf_blend=cfg.shelfBlend,
            shelf_falloff=cfg.shelfFalloff,
            shelf_blur_steps=cfg.shelfBlurSteps,
            peak_mix=cfg.peakMix,
            peak_slope=cfg.peakSlope,
            temp_min_c=float(cfg.tempMinC),
            temp_max_c=float(cfg.tempMaxC),
        )
        if cfg.grayscaleHeightmap:
            generate_grayscale_heightmap(world, f"{work_dir.as_posix()}/{cfg.name}_grayscale.png")
    if isinstance(out_stream, _LogStream):
        out_stream.flush()

    # Verify orbit / climate window against what the temperature preview encodes.
    try:
        import numpy as np

        t = np.asarray(world.temperature, dtype=float)
        _emit(
            "Temperature WE units: "
            f"min={float(t.min()):.3f} mean={float(t.mean()):.3f} max={float(t.max()):.3f} | "
            f"sun={float(cfg.distanceToSun):.2f} | "
            f"in-game window {float(cfg.tempMinC):.0f}...{float(cfg.tempMaxC):.0f} C "
            "(preview uses this C window on a fixed color scale)",
            log,
        )
    except Exception as exc:
        _emit(f"Temperature summary skipped: {exc}", log)

    world_path = work_dir / f"{cfg.name}.world"
    if not world_path.is_file():
        raise FileNotFoundError(f"Expected world file missing: {world_path}")
    _emit(f"World ready: {world_path}", log)
    return world_path


def pack_planet(
    cfg: PlanetConfig,
    world_path: Path,
    work_dir: Path,
    *,
    log: LogFn | None = None,
) -> Path:
    ensure_import_paths()
    from pack_vsplanet import pack_world

    planet_name = cfg.planet_asset_name()
    out_path = work_dir / planet_name
    # Absolute WE temps: orbit distance/tilt bias survives into VS (no min–max stretch).
    _emit(
        f"Packing {world_path.name} -> {out_path.name} (normalizeTemperature=False) ...",
        log,
    )
    pack_world(
        world_path,
        out_path,
        blocks_per_cell=cfg.blocksPerCell,
        normalize_temperature=False,
    )
    if not out_path.is_file():
        raise FileNotFoundError(f"Packer did not write {out_path}")
    _emit(f"Planet ready: {out_path}", log)
    return out_path


def run_pipeline(
    cfg: PlanetConfig,
    *,
    log: LogFn | None = None,
    save_planet_json: bool = True,
    skip_assemble: bool = False,
) -> dict[str, Path]:
    """Generate, pack, and assemble. Returns key paths."""
    apply_climate_extremes(cfg)
    cfg.validate()
    root = user_root()
    work_dir = resolve_output_dir(cfg, root)
    work_dir.mkdir(parents=True, exist_ok=True)

    if save_planet_json:
        save_config(cfg, root / "planet.json")

    world_path = generate_world_files(cfg, work_dir, log=log)
    planet_path = pack_planet(cfg, world_path, work_dir, log=log)

    result: dict[str, Path] = {
        "work_dir": work_dir,
        "world": world_path,
        "planet": planet_path,
    }

    if not skip_assemble:
        zip_path = assemble_mod(cfg, planet_path, work_dir, log=log)
        result["zip"] = zip_path
        result["mod_dir"] = work_dir / f"{cfg.name}-mod"

    _emit("Pipeline complete.", log)
    return result


def preview_paths(cfg: PlanetConfig, work_dir: Path | None = None) -> dict[str, Path]:
    work_dir = work_dir or resolve_output_dir(cfg)
    names = {
        "elevation": f"{cfg.name}_elevation.png",
        "ocean": f"{cfg.name}_ocean.png",
        "temperature": f"{cfg.name}_temperature.png",
        "precipitation": f"{cfg.name}_precipitation.png",
        "biome": f"{cfg.name}_biome.png",
        "grayscale": f"{cfg.name}_grayscale.png",
    }
    return {key: work_dir / name for key, name in names.items()}
