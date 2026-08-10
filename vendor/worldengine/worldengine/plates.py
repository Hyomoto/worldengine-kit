# Every reference to platec has to be kept separated because it is a C
# extension which is not available when using this project from jython

import time

import numpy
import platec

from worldengine.generation import (
    Step,
    add_noise_to_elevation,
    blur_elevation,
    boost_plate_boundary_peaks,
    center_land,
    generate_world,
    get_verbose,
    initialize_ocean_and_thresholds,
    place_oceans_at_map_borders,
    DEFAULT_ELEV_BLUR_STEPS,
    DEFAULT_ELEV_NOISE_AMP,
    DEFAULT_ELEV_NOISE_OCTAVES,
    DEFAULT_NOISY_COASTLINES,
    DEFAULT_PEAK_MIX,
    DEFAULT_PEAK_SLOPE,
    DEFAULT_SHELF_BLEND,
    DEFAULT_SHELF_BLUR_STEPS,
    DEFAULT_SHELF_BREAK,
    DEFAULT_SHELF_DEPTH_NOISE,
    DEFAULT_SHELF_FALLOFF,
    DEFAULT_SHELF_OCEAN_DEPTH,
    DEFAULT_SHELF_RADIUS,
    DEFAULT_SHELF_SHALLOW,
    DEFAULT_SHELF_WIDTH_NOISE,
)
from worldengine.model.world import GenerationParameters, Size, World

# Stronger orogeny / more maturity than stock Mindwerks defaults
DEFAULT_FOLDING_RATIO = 0.06
DEFAULT_PLATE_EROSION_PERIOD = 90
DEFAULT_CYCLE_COUNT = 3
DEFAULT_PLATEC_SEA_LEVEL = 0.65


def generate_plates_simulation(
    seed,
    width,
    height,
    sea_level=DEFAULT_PLATEC_SEA_LEVEL,
    erosion_period=DEFAULT_PLATE_EROSION_PERIOD,
    folding_ratio=DEFAULT_FOLDING_RATIO,
    aggr_overlap_abs=1000000,
    aggr_overlap_rel=0.33,
    cycle_count=DEFAULT_CYCLE_COUNT,
    num_plates=10,
    verbose=get_verbose(),
):
    if verbose:
        start_time = time.time()
    p = platec.create(
        seed,
        width,
        height,
        sea_level,
        erosion_period,
        folding_ratio,
        aggr_overlap_abs,
        aggr_overlap_rel,
        cycle_count,
        num_plates,
    )
    # Note: To rescale the worlds heightmap to roughly Earths scale, multiply by 2000.

    while platec.is_finished(p) == 0:
        platec.step(p)
    hm = platec.get_heightmap(p)
    pm = platec.get_platesmap(p)
    if verbose:
        elapsed_time = time.time() - start_time
        print("...plates.generate_plates_simulation() complete. " + "Elapsed time " + str(elapsed_time) + " seconds.")
    return hm, pm


def _plates_simulation(
    name,
    width,
    height,
    seed,
    temps=[0.874, 0.765, 0.594, 0.439, 0.366, 0.124],
    humids=[0.941, 0.778, 0.507, 0.236, 0.073, 0.014, 0.002],
    gamma_curve=1.25,
    curve_offset=0.2,
    num_plates=10,
    ocean_level=1.0,
    step=Step.full(),
    verbose=get_verbose(),
    folding_ratio=DEFAULT_FOLDING_RATIO,
    plate_erosion_period=DEFAULT_PLATE_EROSION_PERIOD,
    cycle_count=DEFAULT_CYCLE_COUNT,
    platec_sea_level=DEFAULT_PLATEC_SEA_LEVEL,
):
    e_as_array, p_as_array = generate_plates_simulation(
        seed,
        width,
        height,
        sea_level=platec_sea_level,
        erosion_period=plate_erosion_period,
        folding_ratio=folding_ratio,
        cycle_count=cycle_count,
        num_plates=num_plates,
        verbose=verbose,
    )

    world = World(
        name,
        Size(width, height),
        seed,
        GenerationParameters(num_plates, ocean_level, step),
        temps,
        humids,
        gamma_curve,
        curve_offset,
    )
    world.elevation = (numpy.array(e_as_array).reshape(height, width), None)
    world.plates = numpy.array(p_as_array, dtype=numpy.uint16).reshape(height, width)
    return world


def world_gen(
    name,
    width,
    height,
    seed,
    temps=[0.874, 0.765, 0.594, 0.439, 0.366, 0.124],
    humids=[0.941, 0.778, 0.507, 0.236, 0.073, 0.014, 0.002],
    num_plates=10,
    ocean_level=1.0,
    step=Step.full(),
    gamma_curve=1.25,
    curve_offset=0.2,
    fade_borders=True,
    verbose=get_verbose(),
    folding_ratio=DEFAULT_FOLDING_RATIO,
    plate_erosion_period=DEFAULT_PLATE_EROSION_PERIOD,
    cycle_count=DEFAULT_CYCLE_COUNT,
    platec_sea_level=DEFAULT_PLATEC_SEA_LEVEL,
    elev_noise_octaves=DEFAULT_ELEV_NOISE_OCTAVES,
    elev_noise_amp=DEFAULT_ELEV_NOISE_AMP,
    elev_blur_steps=DEFAULT_ELEV_BLUR_STEPS,
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
    peak_mix=DEFAULT_PEAK_MIX,
    peak_slope=DEFAULT_PEAK_SLOPE,
):
    if verbose:
        start_time = time.time()
    world = _plates_simulation(
        name,
        width,
        height,
        seed,
        temps,
        humids,
        gamma_curve,
        curve_offset,
        num_plates,
        ocean_level,
        step,
        verbose,
        folding_ratio=folding_ratio,
        plate_erosion_period=plate_erosion_period,
        cycle_count=cycle_count,
        platec_sea_level=platec_sea_level,
    )

    center_land(world)
    if verbose:
        elapsed_time = time.time() - start_time
        print(
            "...plates.world_gen: set_elevation, set_plates, center_land "
            + "complete. Elapsed time "
            + str(elapsed_time)
            + " seconds."
        )

    if verbose:
        start_time = time.time()
    noise_seed = numpy.random.randint(0, 4096)
    # uses the global RNG; this is the very first call to said RNG - should that change, this needs to be taken care of
    add_noise_to_elevation(world, noise_seed, octaves=elev_noise_octaves, amp=elev_noise_amp)
    if verbose:
        elapsed_time = time.time() - start_time
        print("...plates.world_gen: elevation noise added. Elapsed time " + str(elapsed_time) + " seconds.")

    if verbose:
        start_time = time.time()
    blur_elevation(world, elev_blur_steps)
    if verbose:
        elapsed_time = time.time() - start_time
        print("...plates.world_gen: elevation blur. Elapsed time " + str(elapsed_time) + " seconds.")

    if verbose:
        start_time = time.time()
    boost_plate_boundary_peaks(
        world, ocean_level, peak_mix=peak_mix, peak_slope=peak_slope, seed=seed ^ noise_seed
    )
    if verbose:
        elapsed_time = time.time() - start_time
        print("...plates.world_gen: plate-boundary peak boost. Elapsed time " + str(elapsed_time) + " seconds.")

    if verbose:
        start_time = time.time()
    if fade_borders:
        place_oceans_at_map_borders(world)
    initialize_ocean_and_thresholds(
        world,
        ocean_level=ocean_level,
        shelf_radius=shelf_radius,
        shelf_shallow=shelf_shallow,
        shelf_break=shelf_break,
        noisy_coastlines=noisy_coastlines,
        shelf_width_noise=shelf_width_noise,
        shelf_depth_noise=shelf_depth_noise,
        shelf_ocean_depth=shelf_ocean_depth,
        shelf_blend=shelf_blend,
        shelf_falloff=shelf_falloff,
        shelf_blur_steps=shelf_blur_steps,
        seed=seed,
    )
    if verbose:
        elapsed_time = time.time() - start_time
        print("...plates.world_gen: oceans/shelves initialized. Elapsed time " + str(elapsed_time) + " seconds.")

    return generate_world(world, step)
