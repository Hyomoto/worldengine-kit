"""Initial elevation / ocean generation for WorldEngine.

Maturity note: "look erosion" for older continents is primarily lower elev noise,
land blur, and higher platec erosion_period — not only ErosionSimulation rivers.
"""

from __future__ import annotations

from collections import deque

import numpy
from noise import snoise2

from worldengine.common import anti_alias, get_verbose
from worldengine.map_scale import map_min_dim, resolve_shelf_radius, scale_float, scale_int
from worldengine.model.world import Step
from worldengine.simulations.basic import find_threshold_f
from worldengine.simulations.biome import BiomeSimulation
from worldengine.simulations.erosion import ErosionSimulation
from worldengine.simulations.humidity import HumiditySimulation
from worldengine.simulations.hydrology import WatermapSimulation
from worldengine.simulations.icecap import IcecapSimulation
from worldengine.simulations.irrigation import IrrigationSimulation
from worldengine.simulations.permeability import PermeabilitySimulation
from worldengine.simulations.precipitation import PrecipitationSimulation
from worldengine.simulations.temperature import TemperatureSimulation

# Default terrain-shaping knobs (also CLI defaults)
DEFAULT_ELEV_NOISE_OCTAVES = 4
DEFAULT_ELEV_NOISE_AMP = 0.65
DEFAULT_ELEV_BLUR_STEPS = 2
DEFAULT_SHELF_RADIUS = 0  # 0 = auto from map size (~24 cells at 1024²)
DEFAULT_SHELF_SHALLOW = 0.08
DEFAULT_SHELF_BREAK = 0.65
DEFAULT_SHELF_FALLOFF = 2.2
DEFAULT_SHELF_BLUR_STEPS = 3
DEFAULT_NOISY_COASTLINES = 0.045
DEFAULT_SHELF_WIDTH_NOISE = 0.45
DEFAULT_SHELF_DEPTH_NOISE = 0.4
DEFAULT_SHELF_OCEAN_DEPTH = 1.4
DEFAULT_SHELF_BLEND = 0.3
DEFAULT_PEAK_MIX = 0.55
DEFAULT_PEAK_SLOPE = 12.0

# 8-connected neighbor offsets
_NEIGH8 = (
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
)


# ------------------
# Initial generation
# ------------------


def center_land(world):
    """Translate the map horizontally and vertically to put as much ocean as
    possible at the borders. It operates on elevation and plates map"""

    y_sums = world.layers["elevation"].data.sum(1)  # 1 == sum along x-axis
    y_with_min_sum = y_sums.argmin()
    if get_verbose():
        print("geo.center_land: height complete")

    x_sums = world.layers["elevation"].data.sum(0)  # 0 == sum along y-axis
    x_with_min_sum = x_sums.argmin()
    if get_verbose():
        print("geo.center_land: width complete")

    latshift = 0
    world.layers["elevation"].data = numpy.roll(
        numpy.roll(world.layers["elevation"].data, -y_with_min_sum + latshift, axis=0), -x_with_min_sum, axis=1
    )
    world.layers["plates"].data = numpy.roll(
        numpy.roll(world.layers["plates"].data, -y_with_min_sum + latshift, axis=0), -x_with_min_sum, axis=1
    )
    if get_verbose():
        print("geo.center_land: width complete")


def place_oceans_at_map_borders(world):
    """
    Lower the elevation near the border of the map
    """

    ocean_border = int(min(30, max(world.width / 5, world.height / 5)))
    elev = world.layers["elevation"].data
    height, width = elev.shape

    # Vectorized edge fade (same math as the old per-cell multiply)
    for i in range(ocean_border):
        factor = float(i) / float(ocean_border)
        elev[i, :] *= factor
        elev[height - 1 - i, :] *= factor
        elev[:, i] *= factor
        elev[:, width - 1 - i] *= factor


def simplex_noise_field(height, width, seed, octaves=3, freq=64.0, offset_x=0.0, offset_y=0.0):
    """Build a [-1, 1]-ish simplex field (same snoise2 path as elev noise)."""
    octaves = max(1, int(octaves))
    freq = max(float(freq), 1.0)
    scale = 1.0 / freq
    out = numpy.empty((height, width), dtype=numpy.float64)
    base = int(seed) & 0x7FFFFFFF
    for y in range(height):
        row = out[y]
        ys = (y + offset_y) * scale
        for x in range(width):
            row[x] = snoise2((x + offset_x) * scale, ys, octaves, base=base)
    return out


def add_noise_to_elevation(world, seed, octaves=DEFAULT_ELEV_NOISE_OCTAVES, amp=DEFAULT_ELEV_NOISE_AMP):
    """Add simplex noise to elevation. Wavelength scales with map size (~32 cells at 1024²)."""
    elev = world.layers["elevation"].data
    height, width = elev.shape
    octaves = max(1, int(octaves))
    # Historical default at 1024² with octaves=4 was freq=32 (via 16*octaves then /2).
    freq = scale_float(map_min_dim(width, height), 8.0 * octaves, lo=8.0)
    elev += float(amp) * simplex_noise_field(height, width, seed, octaves=octaves, freq=freq)


def blur_elevation(world, steps=DEFAULT_ELEV_BLUR_STEPS):
    """Low-pass elevation to round coasts and soften plate seams (maturity)."""
    steps = int(steps)
    if steps <= 0:
        return
    world.layers["elevation"].data = anti_alias(world.layers["elevation"].data, steps)


def fill_ocean(elevation, sea_level):
    """Flood-fill ocean from map borders where elev <= sea_level."""
    height, width = elevation.shape
    ocean = numpy.zeros(elevation.shape, dtype=bool)
    q = deque()

    for x in range(width):
        if elevation[0, x] <= sea_level:
            q.append((x, 0))
        if elevation[height - 1, x] <= sea_level:
            q.append((x, height - 1))
    for y in range(height):
        if elevation[y, 0] <= sea_level:
            q.append((0, y))
        if elevation[y, width - 1] <= sea_level:
            q.append((width - 1, y))

    while q:
        tx, ty = q.popleft()
        if ocean[ty, tx]:
            continue
        if elevation[ty, tx] > sea_level:
            continue
        ocean[ty, tx] = True
        for dx, dy in _NEIGH8:
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < width and 0 <= ny < height and not ocean[ny, nx]:
                if elevation[ny, nx] <= sea_level:
                    q.append((nx, ny))

    return ocean


def distance_from_mask(sources, max_radius, jaggedness=0.0, rng=None):
    """
    Multi-source BFS distance field.
    ``sources`` is a bool array True at seed cells (distance 0).
    Cells never reached stay at max_radius + 1.
    Optional jaggedness adds small random cost per step (mapgen4-style).
    """
    height, width = sources.shape
    max_radius = int(max_radius)
    use_jag = jaggedness > 0.0 and rng is not None

    if not use_jag:
        # Fast integer BFS (no re-visits)
        dist = numpy.full((height, width), max_radius + 1, dtype=numpy.int32)
        dist[sources] = 0
        q = deque()
        ys, xs = numpy.nonzero(sources)
        for y, x in zip(ys.tolist(), xs.tolist()):
            q.append((x, y))
        while q:
            x, y = q.popleft()
            d = int(dist[y, x])
            if d >= max_radius:
                continue
            nd = d + 1
            for dx, dy in _NEIGH8:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and dist[ny, nx] > nd:
                    dist[ny, nx] = nd
                    q.append((nx, ny))
        return dist.astype(numpy.float64)

    dist = numpy.full((height, width), max_radius + 1, dtype=numpy.float64)
    dist[sources] = 0.0
    q = deque()
    ys, xs = numpy.nonzero(sources)
    for y, x in zip(ys.tolist(), xs.tolist()):
        q.append((x, y))

    while q:
        x, y = q.popleft()
        d = dist[y, x]
        if d >= max_radius:
            continue
        for dx, dy in _NEIGH8:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            step = 1.0 + jaggedness * (rng.random() - rng.random())
            if step < 0.25:
                step = 0.25
            nd = d + step
            if nd < dist[ny, nx] and nd <= max_radius + 1e-6:
                dist[ny, nx] = nd
                q.append((nx, ny))
    return dist


def shelf_relative_depth(
    dist,
    shelf_radius,
    shelf_shallow=DEFAULT_SHELF_SHALLOW,
    shelf_break=DEFAULT_SHELF_BREAK,
    shelf_falloff=DEFAULT_SHELF_FALLOFF,
):
    """
    Map distance-from-land → relative depth in [0, 1] with a soft falloff.

    Continuous C1 profile (no plateau→cliff kink): near-coast waters stay
    shallow, then deepen smoothly into the abyss. ``shelf_break`` biases how
    long the profile stays shallow; ``shelf_falloff`` is the distance power
    (higher = longer soft shelf). ``shelf_radius`` may be scalar or per-cell.
    """
    shelf_shallow = float(numpy.clip(shelf_shallow, 0.0, 1.0))
    shelf_break = float(numpy.clip(shelf_break, 0.05, 0.95))
    falloff = max(float(shelf_falloff), 0.5)
    dist_f = dist.astype(numpy.float64)
    if numpy.ndim(shelf_radius) == 0:
        radius = max(float(shelf_radius), 1.0)
        t = numpy.clip(dist_f / radius, 0.0, 1.0)
    else:
        radius = numpy.maximum(numpy.asarray(shelf_radius, dtype=numpy.float64), 1.0)
        t = numpy.clip(dist_f / radius, 0.0, 1.0)

    # power > 1 keeps near-shore shallow longer; shelf_break stretches that zone
    power = falloff * (0.5 + shelf_break)
    tw = numpy.power(t, power)
    # smoothstep for C1 ends on the unit interval
    s = tw * tw * (3.0 - 2.0 * tw)
    near = shelf_shallow * 0.4
    depth = near + (1.0 - near) * s
    return numpy.where(t >= 1.0, 1.0, depth)


def blur_ocean_elevation(elevation, ocean, ocean_level, steps=DEFAULT_SHELF_BLUR_STEPS):
    """
    Low-pass ocean bathymetry after the shelf rewrite.
    Land cells are restored so continental peaks stay sharp; ocean is clamped
    below sea level so blur cannot flood the shoreline.
    """
    steps = int(steps)
    if steps <= 0:
        return
    land = ~ocean
    land_vals = elevation[land].copy()
    elevation[:] = anti_alias(elevation, steps)
    elevation[land] = land_vals
    elevation[ocean] = numpy.minimum(elevation[ocean], float(ocean_level) - 1e-4)


def perturb_noisy_coastlines(elevation, ocean_level, amp=DEFAULT_NOISY_COASTLINES, seed=0):
    """
    Mapgen4-style coast warp: add high-freq noise strongest near sea level
    via weight (1 - u^4) so the shoreline is not a hard stencil.
    """
    amp = float(amp)
    if amp <= 0.0:
        return
    height, width = elevation.shape
    soft = max(float(ocean_level) * 0.5, 0.5)
    u = (elevation - ocean_level) / soft
    u_abs = numpy.clip(numpy.abs(u), 0.0, 1.0)
    weight = 1.0 - (u_abs * u_abs * u_abs * u_abs)
    # Blend mid + high frequency like mapgen4 noise4/5/6 mix
    n_mid = simplex_noise_field(height, width, seed + 17, octaves=2, freq=max(width, height) / 24.0)
    n_hi = simplex_noise_field(height, width, seed + 91, octaves=3, freq=max(width, height) / 64.0)
    n = 0.55 * n_mid + 0.45 * n_hi
    elevation += amp * soft * weight * n


def apply_continental_shelves(
    ocean,
    elevation,
    ocean_level,
    shelf_radius=DEFAULT_SHELF_RADIUS,
    shelf_shallow=DEFAULT_SHELF_SHALLOW,
    shelf_break=DEFAULT_SHELF_BREAK,
    seed=0,
    shelf_width_noise=DEFAULT_SHELF_WIDTH_NOISE,
    shelf_depth_noise=DEFAULT_SHELF_DEPTH_NOISE,
    shelf_ocean_depth=DEFAULT_SHELF_OCEAN_DEPTH,
    shelf_blend=DEFAULT_SHELF_BLEND,
    shelf_falloff=DEFAULT_SHELF_FALLOFF,
    shelf_blur_steps=DEFAULT_SHELF_BLUR_STEPS,
):
    """
    Build ocean bathymetry from distance-to-land with mapgen4-inspired variation:
    soft falloff, variable shelf width, alongshore depth noise, residual blend,
    then a light ocean-only blur to clean DF stair-steps.
    Returns (distance_field, relative_depth) for sea_depth reuse.
    """
    land = ~ocean
    if not land.any() or not ocean.any():
        dist = numpy.zeros(elevation.shape, dtype=numpy.float64)
        rel = numpy.zeros(elevation.shape, dtype=numpy.float64)
        return dist, rel

    height, width = elevation.shape
    residual = elevation.copy()
    shelf_radius = resolve_shelf_radius(shelf_radius, width, height)

    width_amp = float(max(shelf_width_noise, 0.0))
    # BFS far enough that widened shelves still resolve
    max_r = int(numpy.ceil(float(shelf_radius) * (1.0 + width_amp) + 4.0))
    max_r = max(max_r, int(shelf_radius))
    dist = distance_from_mask(land, max_radius=max_r)

    if width_amp > 0.0:
        n_width = simplex_noise_field(
            height, width, int(seed) + 3, octaves=3, freq=max(width, height) / 18.0, offset_x=11.0, offset_y=7.0
        )
        local_radius = float(shelf_radius) * (1.0 + width_amp * n_width)
        local_radius = numpy.clip(local_radius, float(shelf_radius) * 0.35, float(shelf_radius) * (1.0 + width_amp))
    else:
        local_radius = float(shelf_radius)

    rel = shelf_relative_depth(dist, local_radius, shelf_shallow, shelf_break, shelf_falloff)

    # Mapgen4 ocean: e *= ocean_depth + noise  → depth varies at fixed distance
    depth_amp = float(max(shelf_depth_noise, 0.0))
    ocean_depth = max(float(shelf_ocean_depth), 0.25)
    if depth_amp > 0.0:
        n_depth = simplex_noise_field(
            height, width, int(seed) + 53, octaves=2, freq=max(width, height) / 28.0, offset_x=23.0, offset_y=19.0
        )
        depth_factor = numpy.clip(ocean_depth + depth_amp * n_depth, 0.2, ocean_depth + depth_amp + 0.5)
        rel = numpy.clip(rel * (depth_factor / ocean_depth), 0.0, 1.0)

    ocean_elev = residual[ocean]
    elev_min = float(ocean_elev.min()) if ocean_elev.size else 0.0
    bathymetry_span = max(ocean_level - elev_min, ocean_level * 0.5, 0.5)
    curve_elev = ocean_level - rel * bathymetry_span

    blend = float(numpy.clip(shelf_blend, 0.0, 1.0))
    if blend > 0.0:
        # Keep residual platec floor, but never above sea
        residual_ocean = numpy.minimum(residual[ocean], ocean_level - 1e-4)
        elevation[ocean] = (1.0 - blend) * curve_elev[ocean] + blend * residual_ocean
    else:
        elevation[ocean] = curve_elev[ocean]

    blur_ocean_elevation(elevation, ocean, ocean_level, steps=shelf_blur_steps)

    # Recompute relative depth from final elev for sea_depth / maps
    final_depth = numpy.clip((ocean_level - elevation) / bathymetry_span, 0.0, 1.0)
    rel = numpy.where(ocean, final_depth, 0.0)
    return dist, rel


def sea_depth_from_relative(rel_depth, ocean, blur_steps=None):
    """Build normalized sea_depth layer from relative shelf depth."""
    result = numpy.zeros(rel_depth.shape, dtype=numpy.float64)
    result[ocean] = rel_depth[ocean]
    if blur_steps is None:
        blur_steps = scale_int(map_min_dim(rel_depth.shape[1], rel_depth.shape[0]), 10, lo=2, hi=12)
    blur_steps = int(blur_steps)
    if blur_steps > 0:
        result = anti_alias(result, blur_steps)
    result[~ocean] = 0.0
    min_depth = float(result.min())
    max_depth = float(result.max())
    if max_depth > min_depth:
        result = (result - min_depth) / (max_depth - min_depth)
    else:
        result = numpy.zeros_like(result)
    result[~ocean] = 0.0
    return result


def sea_depth(
    world,
    sea_level,
    shelf_radius=DEFAULT_SHELF_RADIUS,
    shelf_shallow=DEFAULT_SHELF_SHALLOW,
    shelf_break=DEFAULT_SHELF_BREAK,
    seed=0,
    shelf_width_noise=DEFAULT_SHELF_WIDTH_NOISE,
    shelf_depth_noise=DEFAULT_SHELF_DEPTH_NOISE,
    shelf_ocean_depth=DEFAULT_SHELF_OCEAN_DEPTH,
    shelf_blend=0.0,
    shelf_falloff=DEFAULT_SHELF_FALLOFF,
    shelf_blur_steps=DEFAULT_SHELF_BLUR_STEPS,
):
    """
    Sea depth layer from distance-to-land shelf curve (same as elev rewrite).
    Kept for callers/tests; prefer shared path via initialize_ocean_and_thresholds.
    """
    ocean = world.layers["ocean"].data
    elev = world.layers["elevation"].data.copy()
    _dist, rel = apply_continental_shelves(
        ocean,
        elev,
        sea_level,
        shelf_radius=shelf_radius,
        shelf_shallow=shelf_shallow,
        shelf_break=shelf_break,
        seed=seed,
        shelf_width_noise=shelf_width_noise,
        shelf_depth_noise=shelf_depth_noise,
        shelf_ocean_depth=shelf_ocean_depth,
        shelf_blend=shelf_blend,
        shelf_falloff=shelf_falloff,
        shelf_blur_steps=shelf_blur_steps,
    )
    return sea_depth_from_relative(rel, ocean)


def boost_plate_boundary_peaks(
    world,
    ocean_level,
    peak_mix=DEFAULT_PEAK_MIX,
    peak_slope=DEFAULT_PEAK_SLOPE,
    seed=0,
):
    """
    Amplify ridges along plate boundaries via a peak distance field (mapgen4-style).
    Does not invent continents — only sharpens existing tectonic skeleton.
    """
    peak_mix = float(peak_mix)
    if peak_mix <= 0.0:
        return

    elev = world.layers["elevation"].data
    plates = world.layers["plates"].data
    height, width = elev.shape

    boundary = numpy.zeros((height, width), dtype=bool)
    boundary[:, :-1] |= plates[:, :-1] != plates[:, 1:]
    boundary[:, 1:] |= plates[:, :-1] != plates[:, 1:]
    boundary[:-1, :] |= plates[:-1, :] != plates[1:, :]
    boundary[1:, :] |= plates[:-1, :] != plates[1:, :]

    landish = elev > ocean_level
    candidates = boundary & landish
    if not numpy.any(candidates):
        return

    thr = float(numpy.percentile(elev[candidates], 85))
    seeds = candidates & (elev >= thr)

    # Local maxima along boundary (reinforce peaks)
    padded = numpy.pad(elev, 1, mode="edge")
    center = padded[1:-1, 1:-1]
    is_max = numpy.ones_like(elev, dtype=bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            is_max &= center >= padded[1 + dy : height + 1 + dy, 1 + dx : width + 1 + dx]
    seeds |= candidates & is_max & (elev >= thr)

    if not numpy.any(seeds):
        seeds = candidates & (elev >= thr)
    if not numpy.any(seeds):
        return

    map_scale = max(min(height, width) / 40.0, 1.0)
    max_radius = max(int(map_scale * 2.5), 8)
    # Integer DF (no jagged re-visits) — operational headroom at 2048²
    dist = distance_from_mask(seeds, max_radius=max_radius, jaggedness=0.0, rng=None)

    em = numpy.clip(1.0 - float(peak_slope) / max(map_scale, 1e-3) * dist, 0.01, 1.0)
    em = numpy.where(dist > max_radius, 0.01, em)

    span = max(float(elev.max()) - ocean_level, 1.0)
    land01 = numpy.clip((elev - ocean_level) / span, 0.0, 1.0)
    land01 = numpy.where(landish, land01, 0.0)
    weight = peak_mix * land01 * land01
    target = ocean_level + span * em
    elev[:] = (1.0 - weight) * elev + weight * numpy.maximum(elev, target)


def initialize_ocean_and_thresholds(
    world,
    ocean_level=1.0,
    shelf_radius=DEFAULT_SHELF_RADIUS,
    shelf_shallow=DEFAULT_SHELF_SHALLOW,
    shelf_break=DEFAULT_SHELF_BREAK,
    noisy_coastlines=DEFAULT_NOISY_COASTLINES,
    shelf_width_noise=DEFAULT_SHELF_WIDTH_NOISE,
    shelf_depth_noise=DEFAULT_SHELF_DEPTH_NOISE,
    shelf_ocean_depth=DEFAULT_SHELF_OCEAN_DEPTH,
    shelf_blend=DEFAULT_SHELF_BLEND,
    shelf_falloff=DEFAULT_SHELF_FALLOFF,
    shelf_blur_steps=DEFAULT_SHELF_BLUR_STEPS,
    seed=None,
):
    """
    Calculate the ocean, shelf bathymetry, sea depth and elevation thresholds.
    """
    e = world.layers["elevation"].data
    height, width = e.shape
    shelf_radius = resolve_shelf_radius(shelf_radius, width, height)
    shelf_seed = int(world.seed if seed is None else seed)

    # Warp shoreline before flood-fill so the ocean mask is not a hard stencil
    perturb_noisy_coastlines(e, ocean_level, amp=noisy_coastlines, seed=shelf_seed)

    ocean = fill_ocean(e, ocean_level)
    hl = find_threshold_f(e, 0.10)  # the highest 10% of all (!) land are declared hills
    ml = find_threshold_f(e, 0.03)  # the highest 3% are declared mountains
    e_th = [("sea", ocean_level), ("plain", hl), ("hill", ml), ("mountain", None)]

    _dist, rel = apply_continental_shelves(
        ocean,
        e,
        ocean_level,
        shelf_radius=shelf_radius,
        shelf_shallow=shelf_shallow,
        shelf_break=shelf_break,
        seed=shelf_seed,
        shelf_width_noise=shelf_width_noise,
        shelf_depth_noise=shelf_depth_noise,
        shelf_ocean_depth=shelf_ocean_depth,
        shelf_blend=shelf_blend,
        shelf_falloff=shelf_falloff,
        shelf_blur_steps=shelf_blur_steps,
    )

    world.ocean = ocean
    world.elevation = (e, e_th)
    world.sea_depth = sea_depth_from_relative(rel, ocean)


# Deprecated name kept for imports; shelf rewrite supersedes midpoint crush.
def harmonize_ocean(ocean, elevation, ocean_level):
    """Legacy wrapper — applies shelf-break elev rewrite with defaults."""
    apply_continental_shelves(ocean, elevation, ocean_level)


# ----
# Misc
# ----


def _around(x, y, width, height):
    ps = []
    for dx in range(-1, 2):
        nx = x + dx
        if 0 <= nx < width:
            for dy in range(-1, 2):
                ny = y + dy
                if 0 <= ny < height and (dx != 0 or dy != 0):
                    ps.append((nx, ny))
    return ps


def generate_world(w, step):
    if isinstance(step, str):
        step = Step.get_by_name(step)

    if not step.include_precipitations:
        return w

    # Prepare sufficient seeds for the different steps of the generation
    # create a fresh RNG in case the global RNG is compromised
    # (i.e. has been queried an indefinite amount of times before generate_world() was called)
    rng = numpy.random.RandomState(w.seed)
    # choose lowest common denominator (32 bit Windows numpy cannot handle a larger value)
    sub_seeds = rng.randint(0, numpy.iinfo(numpy.int32).max, size=100)
    # after 0.19.0 do not ever switch out the seeds here to maximize seed-compatibility
    seed_dict = {
        "PrecipitationSimulation": sub_seeds[0],
        "ErosionSimulation": sub_seeds[1],
        "WatermapSimulation": sub_seeds[2],
        "IrrigationSimulation": sub_seeds[3],
        "TemperatureSimulation": sub_seeds[4],
        "HumiditySimulation": sub_seeds[5],
        "PermeabilitySimulation": sub_seeds[6],
        "BiomeSimulation": sub_seeds[7],
        "IcecapSimulation": sub_seeds[8],
        "": sub_seeds[99],
    }

    TemperatureSimulation().execute(w, seed_dict["TemperatureSimulation"])
    # Precipitation with thresholds
    PrecipitationSimulation().execute(w, seed_dict["PrecipitationSimulation"])

    if not step.include_erosion:
        return w
    ErosionSimulation().execute(w, seed_dict["ErosionSimulation"])  # seed not currently used
    if get_verbose():
        print("...erosion calculated")

    WatermapSimulation().execute(w, seed_dict["WatermapSimulation"])  # seed not currently used

    # FIXME: create setters
    IrrigationSimulation().execute(w, seed_dict["IrrigationSimulation"])  # seed not currently used
    HumiditySimulation().execute(w, seed_dict["HumiditySimulation"])  # seed not currently used

    PermeabilitySimulation().execute(w, seed_dict["PermeabilitySimulation"])

    cm, biome_cm = BiomeSimulation().execute(w, seed_dict["BiomeSimulation"])  # seed not currently used
    for cl in cm:
        count = cm[cl]
        if get_verbose():
            print("%s = %i" % (str(cl), count))

    if get_verbose():
        print("")  # empty line
        print("Biome obtained:")

    for cl in biome_cm:
        count = biome_cm[cl]
        if get_verbose():
            print(" %30s = %7i" % (str(cl), count))

    IcecapSimulation().execute(w, seed_dict["IcecapSimulation"])  # makes use of temperature-map

    return w
