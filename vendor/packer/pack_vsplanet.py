#!/usr/bin/env python3
"""Pack a Mindwerks WorldEngine .world protobuf into a tiled .vsplanet atlas."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from vsplanet import (  # noqa: E402
    COMP_DEFLATE,
    LAYER_BIOME,
    LAYER_DIST_OCEAN,
    LAYER_ELEVATION,
    LAYER_ENCLOSURE,
    LAYER_ICECAP,
    LAYER_ISLANDNESS,
    LAYER_LAKE,
    LAYER_OCEAN,
    LAYER_PRECIPITATION,
    LAYER_SEA_DEPTH,
    LAYER_TEMPERATURE,
    LAYER_WETLAND,
    LAYER_CLIFFINESS,
    MAGIC,
    SAMPLE_BIT1,
    SAMPLE_U8,
    SAMPLE_U16,
    TILE_SIZE,
    VERSION,
    LayerInfo,
    PlanetHeader,
    TileIndexEntry,
    compress_payload,
    encode_layer_dir_entry,
    encode_tile_index_entry,
    finalize_header_crc,
    pack_bit1,
    write_header_prefix,
    write_meta,
)

# Historical defaults at 1024²; scaled with map size at pack time.
REF_MAP_SIZE = 1024
ENCLOSURE_RADIUS_REF = 8
DIST_OCEAN_CLAMP_REF = 32.0


def _scale_int(map_min: int, ref_value: float, lo: int, hi: int) -> int:
    v = int(round(float(ref_value) * (float(map_min) / float(REF_MAP_SIZE))))
    return max(lo, min(hi, v))


def _scale_float(map_min: int, ref_value: float, lo: float, hi: float) -> float:
    v = float(ref_value) * (float(map_min) / float(REF_MAP_SIZE))
    return max(lo, min(hi, v))


def _ensure_pb2():
    try:
        import World_pb2  # type: ignore
        return World_pb2
    except ImportError:
        pass
    except Exception as e:
        # Checked-in World_pb2.py validates protobuf runtime 7.35.1; mismatch raises here.
        raise RuntimeError(
            "Failed to import tools/World_pb2.py. Install matching protobuf "
            "(see tools/requirements.txt: protobuf==7.35.1), or delete World_pb2.py "
            f"to regenerate from proto/World.proto. Underlying error: {e}"
        ) from e

    proto = ROOT / "proto" / "World.proto"
    out = Path(__file__).resolve().parent
    try:
        from grpc_tools import protoc
    except ImportError as e:
        raise RuntimeError(
            "World_pb2 missing and grpcio-tools is not installed. "
            "pip install -r tools/requirements.txt"
        ) from e

    rc = protoc.main(
        [
            "protoc",
            f"-I{proto.parent}",
            f"--python_out={out}",
            str(proto),
        ]
    )
    if rc != 0:
        raise RuntimeError(f"protoc failed with code {rc}")
    try:
        import World_pb2  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Regenerated World_pb2.py but import still failed. "
            "Ensure protobuf==7.35.1 is installed (tools/requirements.txt)."
        ) from e

    return World_pb2


def matrix_to_ndarray_f64(matrix) -> np.ndarray:
    rows = [np.asarray(r.cells, dtype=np.float64) for r in matrix.rows]
    return np.vstack(rows)


def matrix_to_ndarray_bool(matrix) -> np.ndarray:
    rows = [np.asarray(r.cells, dtype=np.bool_) for r in matrix.rows]
    return np.vstack(rows)


def matrix_to_ndarray_i32(matrix) -> np.ndarray:
    rows = [np.asarray(r.cells, dtype=np.int32) for r in matrix.rows]
    return np.vstack(rows)


def quantize_u16(data: np.ndarray, vmin: float | None = None, vmax: float | None = None):
    d = np.asarray(data, dtype=np.float64)
    lo = float(np.min(d) if vmin is None else vmin)
    hi = float(np.max(d) if vmax is None else vmax)
    if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
        stored = np.zeros(d.shape, dtype=np.uint16)
        return stored, 0.0, 1.0, 0, 0
    norm = np.clip((d - lo) / (hi - lo), 0.0, 1.0)
    stored = np.rint(norm * 65535.0).astype(np.uint16)
    scale = (hi - lo) / 65535.0
    offset = lo
    return stored, scale, offset, int(stored.min()), int(stored.max())


def quantize_unit_u16(data: np.ndarray):
    """Assume roughly [0,1] unitless WE fields; clamp then fixed-point."""
    d = np.clip(np.asarray(data, dtype=np.float64), 0.0, 1.0)
    stored = np.rint(d * 65535.0).astype(np.uint16)
    return stored, 1.0 / 65535.0, 0.0, int(stored.min()), int(stored.max())


def normalize_temperature_01(
    temp: np.ndarray, land: np.ndarray
) -> tuple[np.ndarray, float, float]:
    """
    Min–max stretch temperature onto [0,1] using land cells (full grid if no land).
    Returns (normalized array, original_lo, original_hi) in WE units.
    """
    d = np.asarray(temp, dtype=np.float64)
    sample = d[land] if np.any(land) else d.reshape(-1)
    lo = float(np.min(sample))
    hi = float(np.max(sample))
    if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
        return np.zeros_like(d), lo, hi
    out = np.clip((d - lo) / (hi - lo), 0.0, 1.0)
    return out, lo, hi


def remap_temperature_threshold(value: float | None, lo: float, hi: float) -> float | None:
    if value is None:
        return None
    span = hi - lo
    if span <= 1e-12:
        return 0.0
    return float(np.clip((float(value) - lo) / span, 0.0, 1.0))


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / max(1e-9, edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def box_mean(mask01: np.ndarray, radius: int) -> np.ndarray:
    """Mean of 0/1 mask in a (2r+1)^2 window via integral image."""
    r = int(radius)
    m = np.asarray(mask01, dtype=np.float64)
    h, w = m.shape
    ii = np.zeros((h + 1, w + 1), dtype=np.float64)
    ii[1:, 1:] = np.cumsum(np.cumsum(m, axis=0), axis=1)
    ys = np.arange(h)[:, None]
    xs = np.arange(w)[None, :]
    y0 = np.maximum(0, ys - r)
    y1 = np.minimum(h, ys + r + 1)
    x0 = np.maximum(0, xs - r)
    x1 = np.minimum(w, xs + r + 1)
    y0b = np.broadcast_to(y0, (h, w))
    y1b = np.broadcast_to(y1, (h, w))
    x0b = np.broadcast_to(x0, (h, w))
    x1b = np.broadcast_to(x1, (h, w))
    total = ii[y1b, x1b] - ii[y0b, x1b] - ii[y1b, x0b] + ii[y0b, x0b]
    area = (y1b - y0b).astype(np.float64) * (x1b - x0b).astype(np.float64)
    return total / np.maximum(area, 1.0)


def label_land_components(land: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """4-connected labels on boolean land. Returns (labels HxW, sizes per label id)."""
    h, w = land.shape
    labels = np.zeros((h, w), dtype=np.int32)
    sizes: list[int] = [0]  # index 0 unused
    next_id = 1
    for y in range(h):
        for x in range(w):
            if not land[y, x] or labels[y, x] != 0:
                continue
            # BFS flood
            stack = [(y, x)]
            labels[y, x] = next_id
            count = 0
            while stack:
                cy, cx = stack.pop()
                count += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if ny < 0 or nx < 0 or ny >= h or nx >= w:
                        continue
                    if not land[ny, nx] or labels[ny, nx] != 0:
                        continue
                    labels[ny, nx] = next_id
                    stack.append((ny, nx))
            sizes.append(count)
            next_id += 1
    return labels, np.asarray(sizes, dtype=np.int32)


def islandness_from_land(land: np.ndarray) -> tuple[np.ndarray, int]:
    labels, sizes = label_land_components(land)
    max_size = int(sizes.max()) if sizes.size > 1 else 1
    max_size = max(max_size, 1)
    log_max = math.log(float(max_size))
    out = np.zeros(land.shape, dtype=np.float64)
    if log_max <= 1e-12:
        out[land] = 1.0
        return out, max_size
    # Vectorized map label → size
    size_map = sizes[labels]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(size_map > 0, np.log(size_map.astype(np.float64)) / log_max, 0.0)
    out = np.where(land, np.clip(1.0 - ratio, 0.0, 1.0), 0.0)
    return out, max_size


def dist_to_ocean(land: np.ndarray, ocean: np.ndarray, clamp_cells: float) -> np.ndarray:
    """Chamfer distance on land cells to nearest ocean; ocean/unknown → 0. Normalized by clamp."""
    h, w = land.shape
    inf = 1e9
    dist = np.full((h, w), inf, dtype=np.float64)
    dist[ocean] = 0.0
    # Forward pass
    for y in range(h):
        for x in range(w):
            d = dist[y, x]
            if y > 0:
                d = min(d, dist[y - 1, x] + 1.0)
            if x > 0:
                d = min(d, dist[y, x - 1] + 1.0)
            if y > 0 and x > 0:
                d = min(d, dist[y - 1, x - 1] + 1.414)
            if y > 0 and x + 1 < w:
                d = min(d, dist[y - 1, x + 1] + 1.414)
            dist[y, x] = d
    # Backward pass
    for y in range(h - 1, -1, -1):
        for x in range(w - 1, -1, -1):
            d = dist[y, x]
            if y + 1 < h:
                d = min(d, dist[y + 1, x] + 1.0)
            if x + 1 < w:
                d = min(d, dist[y, x + 1] + 1.0)
            if y + 1 < h and x + 1 < w:
                d = min(d, dist[y + 1, x + 1] + 1.414)
            if y + 1 < h and x > 0:
                d = min(d, dist[y + 1, x - 1] + 1.414)
            dist[y, x] = d
    out = np.zeros((h, w), dtype=np.float64)
    out[land] = np.clip(dist[land] / max(1e-9, clamp_cells), 0.0, 1.0)
    return out


def derive_wetland(
    land: np.ndarray,
    elev: np.ndarray,
    precip: np.ndarray,
    sea_th: float,
    precip_med: float,
    humidity: np.ndarray | None,
) -> np.ndarray:
    """Soft wetland 0–1 on land: high precip + low height above sea (+ humidity if present)."""
    span = max(1e-4, float(np.percentile(elev[land], 90) - sea_th)) if land.any() else 1.0
    h01 = np.clip((elev - sea_th) / span, 0.0, 1.0)
    flat = 1.0 - smoothstep(0.0, 0.25, h01)
    # precip relative to med threshold
    p_lo = max(0.0, precip_med * 0.5)
    p_hi = min(1.0, precip_med + (1.0 - precip_med) * 0.5) if precip_med < 1 else 1.0
    if precip_med <= 0:
        p_lo, p_hi = 0.35, 0.7
    wet_p = smoothstep(p_lo, p_hi, precip)
    if humidity is not None:
        hum = np.clip(humidity, 0.0, 1.0)
        score = 0.45 * wet_p + 0.35 * flat + 0.20 * hum
    else:
        score = 0.55 * wet_p + 0.45 * flat
    out = np.where(land, np.clip(score, 0.0, 1.0), 0.0)
    return out


def derive_cliffiness(land: np.ndarray, elev: np.ndarray) -> tuple[np.ndarray, float]:
    """Elev gradient magnitude on land, normalized by land p95. Ocean → 0."""
    h, w = elev.shape
    # Central differences with edge clamp
    dx = np.zeros_like(elev, dtype=np.float64)
    dz = np.zeros_like(elev, dtype=np.float64)
    dx[:, 1:-1] = elev[:, 2:] - elev[:, :-2]
    dx[:, 0] = elev[:, 1] - elev[:, 0]
    dx[:, -1] = elev[:, -1] - elev[:, -2]
    dz[1:-1, :] = elev[2:, :] - elev[:-2, :]
    dz[0, :] = elev[1, :] - elev[0, :]
    dz[-1, :] = elev[-1, :] - elev[-2, :]
    grad = np.hypot(dx, dz)
    if land.any():
        p95 = float(np.percentile(grad[land], 95))
    else:
        p95 = 1.0
    p95 = max(p95, 1e-9)
    cliff = np.where(land, np.clip(grad / p95, 0.0, 1.0), 0.0)
    return cliff, p95


def tile_bounds(width: int, height: int, tile: int):
    tiles_x = math.ceil(width / tile)
    tiles_y = math.ceil(height / tile)
    return tiles_x, tiles_y


def iter_tiles(width: int, height: int, tile: int):
    tiles_x, tiles_y = tile_bounds(width, height, tile)
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            x0 = tx * tile
            z0 = ty * tile
            tw = min(tile, width - x0)
            th = min(tile, height - z0)
            yield tx, ty, x0, z0, tw, th


def build_layer_tiles(
    array,
    sample_type: int,
    compression: int = COMP_DEFLATE,
) -> tuple[list[TileIndexEntry], list[bytes]]:
    """array: 2D ndarray matching sample encoding needs."""
    height, width = array.shape
    payloads: list[bytes] = []
    index: list[TileIndexEntry] = []
    for _tx, _ty, x0, z0, tw, th in iter_tiles(width, height, TILE_SIZE):
        block = array[z0 : z0 + th, x0 : x0 + tw]
        if sample_type == SAMPLE_BIT1:
            flat = np.asarray(block, dtype=np.uint8).reshape(-1)
            raw = pack_bit1(bytearray(int(v) for v in flat.tolist()), int(flat.size))
        elif sample_type == SAMPLE_U16:
            raw = np.asarray(block, dtype="<u2").tobytes()
        elif sample_type == SAMPLE_U8:
            raw = np.asarray(block, dtype=np.uint8).tobytes()
        else:
            raise ValueError(sample_type)
        comp = compress_payload(raw, compression)
        index.append(
            TileIndexEntry(
                file_offset=0,
                comp_size=len(comp),
                raw_size=len(raw),
                tile_w=tw,
                tile_h=th,
            )
        )
        payloads.append(comp)
    return index, payloads


def pack_world(
    world_path: Path,
    out_path: Path,
    blocks_per_cell: int = 32,
    normalize_temperature: bool = False,
) -> None:
    World_pb2 = _ensure_pb2()
    raw = world_path.read_bytes()
    world = World_pb2.World()
    world.ParseFromString(raw)

    width = int(world.width)
    height = int(world.height)
    print(f"Loaded {world.name!r} {width}x{height} ({len(raw)} bytes protobuf)")

    ocean = matrix_to_ndarray_bool(world.ocean)
    temp = matrix_to_ndarray_f64(world.temperatureData)
    precip = matrix_to_ndarray_f64(world.precipitationData)
    elev = matrix_to_ndarray_f64(world.heightMapData)
    sea_depth = matrix_to_ndarray_f64(world.sea_depth)
    biome = matrix_to_ndarray_i32(world.biome) if world.HasField("biome") else np.zeros((height, width), dtype=np.int32)

    has_lakemap = world.HasField("lakemap")
    has_icecap = world.HasField("icecap")
    lake = matrix_to_ndarray_f64(world.lakemap) if has_lakemap else np.zeros((height, width), dtype=np.float64)
    icecap = matrix_to_ndarray_f64(world.icecap) if has_icecap else np.zeros((height, width), dtype=np.float64)
    if has_lakemap and float(np.max(lake)) > 1.0 + 1e-6:
        lo, hi = float(np.min(lake)), float(np.max(lake))
        lake = (lake - lo) / max(1e-9, hi - lo)
    else:
        lake = np.clip(lake, 0.0, 1.0)
    if has_icecap and float(np.max(icecap)) > 1.0 + 1e-6:
        lo, hi = float(np.min(icecap)), float(np.max(icecap))
        icecap = (icecap - lo) / max(1e-9, hi - lo)
    else:
        icecap = np.clip(icecap, 0.0, 1.0)
    humidity = None
    if world.HasField("humidity") and len(world.humidity.rows) > 0:
        humidity = matrix_to_ndarray_f64(world.humidity)
        humidity = np.clip(humidity, 0.0, 1.0)

    if ocean.shape != (height, width):
        raise ValueError(f"ocean shape {ocean.shape} != {(height, width)}")
    if sea_depth.shape != (height, width):
        raise ValueError(f"sea_depth shape {sea_depth.shape} != {(height, width)}")

    land = ~ocean
    sea_th = float(world.heightMapTh_sea)
    precip_med = float(world.precipitation_med) if world.HasField("precipitation_med") else 0.5
    map_min = int(min(height, width))
    enclosure_radius = _scale_int(map_min, ENCLOSURE_RADIUS_REF, lo=4, hi=16)
    dist_ocean_clamp = _scale_float(map_min, DIST_OCEAN_CLAMP_REF, lo=16.0, hi=64.0)

    temp_norm_lo = temp_norm_hi = None
    if normalize_temperature:
        temp, temp_norm_lo, temp_norm_hi = normalize_temperature_01(temp, land)
        print(
            f"Normalized temperature to [0,1] from land WE range "
            f"[{temp_norm_lo:.6f},{temp_norm_hi:.6f}]"
        )

    print("Deriving enclosure / islandness / distOcean / wetland / cliffiness…")
    enclosure = box_mean(land.astype(np.float64), enclosure_radius)
    islandness, island_max_component = islandness_from_land(land)
    dist_ocean = dist_to_ocean(land, ocean, dist_ocean_clamp)
    wetland = derive_wetland(land, elev, precip, sea_th, precip_med, humidity)
    cliffiness, cliff_p95 = derive_cliffiness(land, elev)

    lake_u16, lk_scale, lk_off, lk_min, lk_max = quantize_unit_u16(lake)
    ice_u16, ice_scale, ice_off, ice_min, ice_max = quantize_unit_u16(icecap)
    enc_u16, enc_scale, enc_off, enc_min, enc_max = quantize_unit_u16(enclosure)
    isl_u16, isl_scale, isl_off, isl_min, isl_max = quantize_unit_u16(islandness)
    do_u16, do_scale, do_off, do_min, do_max = quantize_unit_u16(dist_ocean)
    wet_u16, wet_scale, wet_off, wet_min, wet_max = quantize_unit_u16(wetland)
    cliff_u16, cliff_scale, cliff_off, cliff_min, cliff_max = quantize_unit_u16(cliffiness)

    lake_nz = int(np.count_nonzero(lake > 1e-6))
    ice_nz = int(np.count_nonzero(icecap > 1e-6))
    wet_hi = int(np.count_nonzero(wetland >= 0.55))
    isl_hi = int(np.count_nonzero(islandness >= 0.45))
    cliff_hi = int(np.count_nonzero(cliffiness >= 0.45))
    print(
        f"  lake nonzero={lake_nz} (has={has_lakemap}) icecap nonzero={ice_nz} (has={has_icecap}) "
        f"island_max={island_max_component} islandish_cells={isl_hi} wetland>=0.55={wet_hi} "
        f"cliff>=0.45={cliff_hi} cliff_p95={cliff_p95:.6f}"
    )

    temp_u16, t_scale, t_off, t_min, t_max = quantize_unit_u16(temp)
    precip_u16, p_scale, p_off, p_min, p_max = quantize_unit_u16(precip)
    elev_u16, e_scale, e_off, e_min, e_max = quantize_u16(elev)
    sea_u16, sd_scale, sd_off, sd_min, sd_max = quantize_unit_u16(sea_depth)
    biome_u8 = np.clip(biome, 0, 255).astype(np.uint8)

    ocean_sd = sea_depth[ocean]
    if ocean_sd.size == 0:
        sd_p10 = sd_p50 = sd_p90 = 0.0
    else:
        sd_p10, sd_p50, sd_p90 = (float(x) for x in np.percentile(ocean_sd, [10, 50, 90]))

    # Continuous bathymetry on ocean cells: sea - elev (primary OceanMap driver).
    bath = sea_th - elev
    ocean_bath = bath[ocean]
    if ocean_bath.size == 0:
        bath_p01 = bath_p10 = bath_p50 = bath_p90 = 0.0
    else:
        bath_p01, bath_p10, bath_p50, bath_p90 = (
            float(x) for x in np.percentile(ocean_bath, [1, 10, 50, 90])
        )

    meta = {
        "name": world.name,
        "packer": "worldengine/tools/pack_vsplanet.py",
        "source": str(world_path.name),
        "heightMapTh_sea": world.heightMapTh_sea,
        "heightMapTh_plain": world.heightMapTh_plain,
        "heightMapTh_hill": world.heightMapTh_hill,
        "precipitation_low": world.precipitation_low if world.HasField("precipitation_low") else None,
        "precipitation_med": world.precipitation_med if world.HasField("precipitation_med") else None,
        "temperature_polar": world.temperature_polar if world.HasField("temperature_polar") else None,
        "temperature_alpine": world.temperature_alpine if world.HasField("temperature_alpine") else None,
        "temperature_boreal": world.temperature_boreal if world.HasField("temperature_boreal") else None,
        "temperature_cool": world.temperature_cool if world.HasField("temperature_cool") else None,
        "temperature_warm": world.temperature_warm if world.HasField("temperature_warm") else None,
        "temperature_subtropical": world.temperature_subtropical if world.HasField("temperature_subtropical") else None,
        "temperature_normalized": bool(normalize_temperature),
        "elevation_decode_min": e_off,
        "elevation_decode_max": e_off + e_scale * 65535.0,
        # OceanMap stretch uses p01..p90 so cyan shelf/inlets vary (p10 flattened them).
        "bath_ocean_p01": bath_p01,
        "bath_ocean_p10": bath_p10,
        "bath_ocean_p50": bath_p50,
        "bath_ocean_p90": bath_p90,
        # Optional seaDepth percentiles (OceanMap uses elev bathymetry at runtime).
        "sea_depth_ocean_p10": sd_p10,
        "sea_depth_ocean_p50": sd_p50,
        "sea_depth_ocean_p90": sd_p90,
        "has_lakemap": has_lakemap,
        "has_icecap": has_icecap,
        "island_max_component": island_max_component,
        "enclosure_radius": enclosure_radius,
        "dist_ocean_clamp": dist_ocean_clamp,
        "has_cliffiness": True,
        "cliff_p95": cliff_p95,
    }
    if normalize_temperature and temp_norm_lo is not None and temp_norm_hi is not None:
        meta["temperature_norm_lo"] = temp_norm_lo
        meta["temperature_norm_hi"] = temp_norm_hi
        for key in (
            "temperature_polar",
            "temperature_alpine",
            "temperature_boreal",
            "temperature_cool",
            "temperature_warm",
            "temperature_subtropical",
        ):
            meta[key] = remap_temperature_threshold(meta.get(key), temp_norm_lo, temp_norm_hi)

    if world.HasField("generationData"):
        gd = world.generationData
        meta["seed"] = gd.seed if gd.HasField("seed") else None
        meta["n_plates"] = gd.n_plates if gd.HasField("n_plates") else None
        meta["ocean_level"] = gd.ocean_level if gd.HasField("ocean_level") else None
        meta["step"] = gd.step if gd.HasField("step") else None

    tiles_x, tiles_y = tile_bounds(width, height, TILE_SIZE)
    layer_specs = [
        (LAYER_OCEAN, "ocean", SAMPLE_BIT1, 0, ocean.astype(np.uint8), 1.0, 0.0, 0, 1),
        (LAYER_TEMPERATURE, "temperature", SAMPLE_U16, 2, temp_u16, t_scale, t_off, t_min, t_max),
        (LAYER_PRECIPITATION, "precipitation", SAMPLE_U16, 2, precip_u16, p_scale, p_off, p_min, p_max),
        (LAYER_ELEVATION, "elevation", SAMPLE_U16, 2, elev_u16, e_scale, e_off, e_min, e_max),
        (LAYER_BIOME, "biome", SAMPLE_U8, 1, biome_u8, 1.0, 0.0, int(biome_u8.min()), int(biome_u8.max())),
        (LAYER_SEA_DEPTH, "seaDepth", SAMPLE_U16, 2, sea_u16, sd_scale, sd_off, sd_min, sd_max),
        (LAYER_LAKE, "lake", SAMPLE_U16, 2, lake_u16, lk_scale, lk_off, lk_min, lk_max),
        (LAYER_ICECAP, "icecap", SAMPLE_U16, 2, ice_u16, ice_scale, ice_off, ice_min, ice_max),
        (LAYER_ENCLOSURE, "enclosure", SAMPLE_U16, 2, enc_u16, enc_scale, enc_off, enc_min, enc_max),
        (LAYER_ISLANDNESS, "islandness", SAMPLE_U16, 2, isl_u16, isl_scale, isl_off, isl_min, isl_max),
        (LAYER_DIST_OCEAN, "distOcean", SAMPLE_U16, 2, do_u16, do_scale, do_off, do_min, do_max),
        (LAYER_WETLAND, "wetland", SAMPLE_U16, 2, wet_u16, wet_scale, wet_off, wet_min, wet_max),
        (LAYER_CLIFFINESS, "cliffiness", SAMPLE_U16, 2, cliff_u16, cliff_scale, cliff_off, cliff_min, cliff_max),
    ]

    built = []
    for layer_id, name, stype, bps, arr, scale, offset, mn, mx in layer_specs:
        index, payloads = build_layer_tiles(arr, stype, COMP_DEFLATE)
        built.append(
            (
                LayerInfo(
                    layer_id=layer_id,
                    sample_type=stype,
                    compression=COMP_DEFLATE,
                    bytes_per_sample=bps,
                    scale=float(scale),
                    offset=float(offset),
                    min_stored=mn,
                    max_stored=mx,
                    name=name,
                ),
                index,
                payloads,
            )
        )

    header = PlanetHeader(
        magic=MAGIC,
        version=VERSION,
        flags=0,
        width=width,
        height=height,
        blocks_per_cell=blocks_per_cell,
        tile_size=TILE_SIZE,
        tiles_x=tiles_x,
        tiles_y=tiles_y,
        layer_count=len(built),
        meta=meta,
    )

    # Pass 1: size header + meta + layer dir (with placeholder offsets) + tile indexes
    buf = bytearray()
    write_header_prefix(buf, header)
    finalize_header_crc(buf)
    write_meta(buf, meta)

    layer_dir_start = len(buf)
    # We'll rewrite layer dir after we know tile index offsets
    placeholder_dirs = []
    for layer, index, payloads in built:
        placeholder_dirs.append(encode_layer_dir_entry(layer))
        buf += placeholder_dirs[-1]

    # Record where each tile index will live
    tile_index_offsets = []
    for layer, index, payloads in built:
        tile_index_offsets.append(len(buf))
        buf += b"\x00" * (len(index) * (8 + 4 + 4 + 2 + 2))

    # Append payloads; fill real tile offsets
    final_indexes: list[list[TileIndexEntry]] = []
    for layer, index, payloads in built:
        fixed_index = []
        for entry, payload in zip(index, payloads):
            entry.file_offset = len(buf)
            buf += payload
            fixed_index.append(entry)
        final_indexes.append(fixed_index)

    # Patch tile index tables
    for off, fixed_index in zip(tile_index_offsets, final_indexes):
        blob = b"".join(encode_tile_index_entry(e) for e in fixed_index)
        buf[off : off + len(blob)] = blob

    # Patch layer directory tile_index_offset fields
    # Rebuild layer dir at layer_dir_start
    dir_blob = bytearray()
    for (layer, _index, _payloads), tio in zip(built, tile_index_offsets):
        layer.tile_index_offset = tio
        dir_blob += encode_layer_dir_entry(layer)
    assert len(dir_blob) == sum(len(p) for p in placeholder_dirs)
    buf[layer_dir_start : layer_dir_start + len(dir_blob)] = dir_blob

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(buf)
    print(f"Wrote {out_path} ({len(buf)} bytes), {tiles_x}x{tiles_y} tiles, {len(built)} layers")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("world", type=Path, help="Input .world protobuf")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output .vsplanet path")
    ap.add_argument("--blocks-per-cell", type=int, default=32)
    ap.add_argument(
        "--normalize-temperature",
        action="store_true",
        help=(
            "Min–max stretch land temperature to [0,1] so VS tempMinC..tempMaxC uses the full spectrum. "
            "Default keeps absolute WE units (cold planets stay cold). Remaps temperature_* meta thresholds."
        ),
    )
    args = ap.parse_args()
    pack_world(
        args.world,
        args.output,
        args.blocks_per_cell,
        normalize_temperature=args.normalize_temperature,
    )


if __name__ == "__main__":
    main()
