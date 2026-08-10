"""Map-size relative knobs.

Values are tuned so historical defaults match at REF_SIZE (1024). Larger maps
get proportionally larger cell-space radii; smaller maps get tighter ones.
"""

from __future__ import annotations

REF_SIZE = 1024


def map_min_dim(width: int, height: int) -> int:
    return int(min(width, height))


def scale_int(map_min: int, ref_value: float, ref_size: int = REF_SIZE, lo: int | None = None, hi: int | None = None) -> int:
    v = int(round(float(ref_value) * (float(map_min) / float(ref_size))))
    if lo is not None:
        v = max(int(lo), v)
    if hi is not None:
        v = min(int(hi), v)
    return v


def scale_float(
    map_min: int, ref_value: float, ref_size: int = REF_SIZE, lo: float | None = None, hi: float | None = None
) -> float:
    v = float(ref_value) * (float(map_min) / float(ref_size))
    if lo is not None:
        v = max(float(lo), v)
    if hi is not None:
        v = min(float(hi), v)
    return v


def auto_shelf_radius(width: int, height: int) -> int:
    """Continental shelf width in cells (~24 at 1024²)."""
    return scale_int(map_min_dim(width, height), 24, lo=8, hi=64)


def resolve_shelf_radius(shelf_radius: int | None, width: int, height: int) -> int:
    """``<= 0`` or ``None`` means auto from map size."""
    if shelf_radius is None or int(shelf_radius) <= 0:
        return auto_shelf_radius(width, height)
    return int(shelf_radius)
