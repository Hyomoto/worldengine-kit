"""Shared .vsplanet v1 constants and codec helpers."""

from __future__ import annotations

import json
import struct
import zlib
from dataclasses import dataclass, field
from typing import BinaryIO

MAGIC = 0x4C505356  # VSPL little-endian
VERSION = 1
TILE_SIZE = 256

LAYER_OCEAN = 1
LAYER_TEMPERATURE = 2
LAYER_PRECIPITATION = 3
LAYER_ELEVATION = 4
LAYER_BIOME = 5
LAYER_SEA_DEPTH = 6
# Additive specialty / derived layers (format version stays 1)
LAYER_LAKE = 7
LAYER_ICECAP = 8
LAYER_ENCLOSURE = 9
LAYER_ISLANDNESS = 10
LAYER_DIST_OCEAN = 11
LAYER_WETLAND = 12
LAYER_CLIFFINESS = 13

SAMPLE_U8 = 0
SAMPLE_U16 = 1
SAMPLE_I16 = 2
SAMPLE_BIT1 = 3

COMP_NONE = 0
COMP_DEFLATE = 1

HEADER_STRUCT = struct.Struct("<IHHIIIHHHH")  # magic, ver, flags, w, h, bpc, tileSize, tilesX, tilesY, layerCount (28 bytes); CRC follows


@dataclass
class LayerInfo:
    layer_id: int
    sample_type: int
    compression: int
    bytes_per_sample: int
    scale: float
    offset: float
    min_stored: int
    max_stored: int
    tile_index_offset: int = 0
    name: str = ""


@dataclass
class TileIndexEntry:
    file_offset: int
    comp_size: int
    raw_size: int
    tile_w: int
    tile_h: int


@dataclass
class PlanetHeader:
    magic: int = MAGIC
    version: int = VERSION
    flags: int = 0
    width: int = 0
    height: int = 0
    blocks_per_cell: int = 32
    tile_size: int = TILE_SIZE
    tiles_x: int = 0
    tiles_y: int = 0
    layer_count: int = 0
    header_crc32: int = 0
    meta: dict = field(default_factory=dict)
    layers: list[LayerInfo] = field(default_factory=list)


def pack_bit1(mask: bytes | bytearray, count: int) -> bytes:
    """Pack boolean/0-1 samples into Bit1 bytes (MSB first)."""
    out = bytearray((count + 7) // 8)
    for i in range(count):
        if mask[i]:
            out[i >> 3] |= 0x80 >> (i & 7)
    return bytes(out)


def unpack_bit1(data: bytes, count: int) -> bytearray:
    out = bytearray(count)
    for i in range(count):
        out[i] = 1 if (data[i >> 3] & (0x80 >> (i & 7))) else 0
    return out


def compress_payload(raw: bytes, compression: int = COMP_DEFLATE) -> bytes:
    if compression == COMP_NONE:
        return raw
    if compression == COMP_DEFLATE:
        return zlib.compress(raw, level=6)
    raise ValueError(f"unknown compression {compression}")


def decompress_payload(data: bytes, raw_size: int, compression: int = COMP_DEFLATE) -> bytes:
    if compression == COMP_NONE:
        return data
    if compression == COMP_DEFLATE:
        out = zlib.decompress(data)
        if len(out) != raw_size:
            raise ValueError(f"raw size mismatch: got {len(out)} expected {raw_size}")
        return out
    raise ValueError(f"unknown compression {compression}")


def write_header_prefix(buf: bytearray, h: PlanetHeader) -> None:
    buf += HEADER_STRUCT.pack(
        h.magic,
        h.version,
        h.flags,
        h.width,
        h.height,
        h.blocks_per_cell,
        h.tile_size,
        h.tiles_x,
        h.tiles_y,
        h.layer_count,
    )


def finalize_header_crc(buf: bytearray) -> None:
    """Append CRC32 of current header bytes (magic..layerCount)."""
    crc = zlib.crc32(buf) & 0xFFFFFFFF
    buf += struct.pack("<I", crc)


def write_meta(buf: bytearray, meta: dict) -> None:
    raw = json.dumps(meta, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    buf += struct.pack("<I", len(raw))
    buf += raw


def encode_layer_dir_entry(layer: LayerInfo) -> bytes:
    name_b = layer.name.encode("utf-8")
    return struct.pack(
        "<BBBBffHHQH",
        layer.layer_id,
        layer.sample_type,
        layer.compression,
        layer.bytes_per_sample,
        layer.scale,
        layer.offset,
        layer.min_stored & 0xFFFF,
        layer.max_stored & 0xFFFF,
        layer.tile_index_offset & 0xFFFFFFFFFFFFFFFF,
        len(name_b),
    ) + name_b


def encode_tile_index_entry(e: TileIndexEntry) -> bytes:
    return struct.pack(
        "<QIIHH",
        e.file_offset,
        e.comp_size,
        e.raw_size,
        e.tile_w,
        e.tile_h,
    )


def read_exact(f: BinaryIO, n: int) -> bytes:
    data = f.read(n)
    if len(data) != n:
        raise EOFError(f"expected {n} bytes, got {len(data)}")
    return data


def read_planet_header(f: BinaryIO) -> PlanetHeader:
    raw = read_exact(f, HEADER_STRUCT.size)
    magic, version, flags, width, height, bpc, tile_size, tiles_x, tiles_y, layer_count = HEADER_STRUCT.unpack(raw)
    crc_bytes = read_exact(f, 4)
    crc = struct.unpack("<I", crc_bytes)[0]
    expect = zlib.crc32(raw) & 0xFFFFFFFF
    if magic != MAGIC:
        raise ValueError(f"bad magic {magic:#x}")
    if version != VERSION:
        raise ValueError(f"unsupported version {version}")
    if crc != expect:
        raise ValueError(f"header CRC mismatch {crc:#x} != {expect:#x}")

    meta_len = struct.unpack("<I", read_exact(f, 4))[0]
    meta = json.loads(read_exact(f, meta_len).decode("utf-8")) if meta_len else {}

    layers: list[LayerInfo] = []
    for _ in range(layer_count):
        fixed = read_exact(f, 1 + 1 + 1 + 1 + 4 + 4 + 2 + 2 + 8 + 2)
        (
            layer_id,
            sample_type,
            compression,
            bytes_per_sample,
            scale,
            offset,
            min_stored,
            max_stored,
            tile_index_offset,
            name_len,
        ) = struct.unpack("<BBBBffHHQH", fixed)
        name = read_exact(f, name_len).decode("utf-8") if name_len else ""
        layers.append(
            LayerInfo(
                layer_id=layer_id,
                sample_type=sample_type,
                compression=compression,
                bytes_per_sample=bytes_per_sample,
                scale=scale,
                offset=offset,
                min_stored=min_stored,
                max_stored=max_stored,
                tile_index_offset=tile_index_offset,
                name=name,
            )
        )

    return PlanetHeader(
        magic=magic,
        version=version,
        flags=flags,
        width=width,
        height=height,
        blocks_per_cell=bpc,
        tile_size=tile_size,
        tiles_x=tiles_x,
        tiles_y=tiles_y,
        layer_count=layer_count,
        header_crc32=crc,
        meta=meta,
        layers=layers,
    )


def read_tile_index(f: BinaryIO, count: int) -> list[TileIndexEntry]:
    entries: list[TileIndexEntry] = []
    for _ in range(count):
        raw = read_exact(f, 8 + 4 + 4 + 2 + 2)
        off, cs, rs, tw, th = struct.unpack("<QIIHH", raw)
        entries.append(TileIndexEntry(off, cs, rs, tw, th))
    return entries
