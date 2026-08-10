"""Planet config schema with consequence-oriented field metadata."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Iterator

from planetkit.paths import kit_root, user_root

def _presets_dir() -> Path:
    return kit_root() / "presets"


def _default_planet_json() -> Path:
    return user_root() / "planet.json"


# Back-compat aliases (resolved at import; prefer helpers above when freezing)
KIT_ROOT = kit_root()
PRESETS_DIR = KIT_ROOT / "presets"
DEFAULT_PLANET_JSON = KIT_ROOT / "planet.json"


@dataclass
class FieldMeta:
    key: str
    label: str
    group: str
    default: Any
    effect: str
    in_game: str
    up: str
    down: str
    min_value: float | int | None = None
    max_value: float | int | None = None
    step: float | int | None = None
    kind: str = "float"  # float | int | bool | str | choice
    choices: tuple[str, ...] = ()
    easy: bool = False


# Generation + pack fields (advanced unless easy=True)
FIELD_META: tuple[FieldMeta, ...] = (
    FieldMeta(
        key="name",
        label="World name",
        group="easy",
        default="example",
        effect="Sets output file names (.world, previews, .vsplanet, mod zip).",
        in_game="Only affects asset naming inside the mod zip.",
        up="Use a short lowercase id without spaces.",
        down="—",
        kind="str",
        easy=True,
    ),
    FieldMeta(
        key="seed",
        label="Seed",
        group="easy",
        default=69,
        effect="Initializes all procedural noise and plate layout.",
        in_game="Same seed + same settings → same planet. Change seed for a new layout.",
        up="Different continents and climates.",
        down="—",
        kind="int",
        min_value=0,
        max_value=2_147_483_647,
        easy=True,
    ),
    FieldMeta(
        key="width",
        label="Width (cells)",
        group="easy",
        default=2048,
        effect="Horizontal resolution of the planet grid. Larger maps take much longer.",
        in_game="With Fit scale, the whole planet stretches over the VS map. More cells = finer coasts before stretch.",
        up="More detail, slower generation, larger .vsplanet.",
        down="Faster; coasts look coarser when stretched to a large world.",
        kind="int",
        min_value=256,
        max_value=4096,
        step=256,
        easy=True,
    ),
    FieldMeta(
        key="height",
        label="Height (cells)",
        group="easy",
        default=2048,
        effect="Vertical resolution of the planet grid.",
        in_game="Same as width for Fit mode; prefer square maps unless you know you want stretch.",
        up="More detail / slower.",
        down="Faster / coarser.",
        kind="int",
        min_value=256,
        max_value=4096,
        step=256,
        easy=True,
    ),
    FieldMeta(
        key="preset",
        label="Style preset",
        group="easy",
        default="balanced",
        effect="Loads a named bundle of generation knobs (plates, shelf, peaks, etc.).",
        in_game="Quick starting point; you can still tweak advanced fields afterward.",
        up="Pick the outcome you want, then fine-tune.",
        down="—",
        kind="choice",
        choices=("balanced", "continental", "archipelago"),
        easy=True,
    ),
    FieldMeta(
        key="normalizeTemperature",
        label="Normalize temperature",
        group="easy",
        default=True,
        effect="At pack time, stretches land temperature onto [0,1] from that planet's land min–max.",
        in_game="ON (default): VS sees the full −20…40 °C spectrum so all biomes can appear. OFF: a cold WE orbit stays cold.",
        up="Full biome spectrum from whatever WE produced.",
        down="Preserve absolute WE cold/hot bias (intentionally harsh climates).",
        kind="bool",
        easy=True,
    ),
    FieldMeta(
        key="numberOfPlates",
        label="Number of plates",
        group="tectonics",
        default=7,
        effect="How many tectonic plates compete during platec simulation.",
        in_game="More plates → more fragmented continents and island chains; fewer → larger landmasses.",
        up="Archipelagos, broken coasts, more plate-boundary mountains.",
        down="Big continents, simpler coast outlines.",
        kind="int",
        min_value=3,
        max_value=20,
        step=1,
    ),
    FieldMeta(
        key="foldingRatio",
        label="Folding ratio",
        group="tectonics",
        default=0.06,
        effect="Platec orogeny strength when plates collide.",
        in_game="Stronger folding → taller / sharper mountain belts along plate edges.",
        up="Younger, punchier ranges.",
        down="Gentler hills; mountains less dominant.",
        kind="float",
        min_value=0.0,
        max_value=0.3,
        step=0.01,
    ),
    FieldMeta(
        key="plateErosionPeriod",
        label="Plate erosion period",
        group="tectonics",
        default=90,
        effect="Tectonic erosion interval inside platec (higher = more mature landscape).",
        in_game="Higher values wear sharp uplift into softer, older-looking terrain.",
        up="More mature / rounded relief.",
        down="Rougher, less eroded uplift.",
        kind="int",
        min_value=10,
        max_value=200,
        step=5,
    ),
    FieldMeta(
        key="cycleCount",
        label="Simulation cycles",
        group="tectonics",
        default=3,
        effect="How many platec simulation cycles to run.",
        in_game="More cycles deepen plate interaction (coasts and ranges evolve further).",
        up="More developed tectonics (slower).",
        down="Faster, simpler plate layout.",
        kind="int",
        min_value=1,
        max_value=8,
        step=1,
    ),
    FieldMeta(
        key="elevNoiseOctaves",
        label="Elevation noise octaves",
        group="relief",
        default=4,
        effect="Simplex octaves added on top of plate elevation.",
        in_game="Adds fine hills and texture instead of pure tectonic slabs.",
        up="Richer local roughness.",
        down="Smoother, more 'plate-only' land.",
        kind="int",
        min_value=0,
        max_value=8,
        step=1,
    ),
    FieldMeta(
        key="elevNoiseAmp",
        label="Elevation noise amplitude",
        group="relief",
        default=0.65,
        effect="Strength of elevation noise relative to plate heights.",
        in_game="Higher → bumpier interiors and noisier coastlines before shelf rewrite.",
        up="Craggy / irregular terrain.",
        down="Cleaner large-scale shapes.",
        kind="float",
        min_value=0.0,
        max_value=2.0,
        step=0.05,
    ),
    FieldMeta(
        key="elevBlurSteps",
        label="Elevation blur passes",
        group="relief",
        default=2,
        effect="Anti-alias passes on elevation before ocean classification.",
        in_game="Softens jagged height artifacts; too much can melt sharp ridges.",
        up="Smoother heightfields.",
        down="Crisper (possibly noisier) relief.",
        kind="int",
        min_value=0,
        max_value=8,
        step=1,
    ),
    FieldMeta(
        key="peakMix",
        label="Peak mix",
        group="relief",
        default=0.55,
        effect="Weight of plate-boundary mountain boost.",
        in_game="How strongly mountain belts punch above surrounding land.",
        up="Dramatic ranges / highland belts.",
        down="Flatter continents; mountains less special.",
        kind="float",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
    ),
    FieldMeta(
        key="peakSlope",
        label="Peak slope",
        group="relief",
        default=12.0,
        effect="Distance-field falloff for mountain boost.",
        in_game="Higher → peaks stay narrow; lower → wide highland shoulders.",
        up="Narrower mountain spines.",
        down="Broader elevated regions.",
        kind="float",
        min_value=1.0,
        max_value=40.0,
        step=1.0,
    ),
    FieldMeta(
        key="shelfRadius",
        label="Shelf radius",
        group="coasts",
        default=0,
        effect="Continental shelf width in cells; 0 = auto from map size (~24 at 1024).",
        in_game="Controls how wide the soft nearshore bathymetry band is before deep ocean.",
        up="Wider shelves / longer shallows (explicit cell count).",
        down="0 keeps auto scaling; small values pinch the shelf.",
        kind="int",
        min_value=0,
        max_value=128,
        step=1,
    ),
    FieldMeta(
        key="shelfShallow",
        label="Shelf shallow floor",
        group="coasts",
        default=0.08,
        effect="Near-coast relative depth floor on the soft shelf curve.",
        in_game="Keeps immediate offshore water from snapping to deep marine too soon.",
        up="Shallower nearshore flats.",
        down="Steeper drop just off the beach.",
        kind="float",
        min_value=0.0,
        max_value=0.5,
        step=0.01,
    ),
    FieldMeta(
        key="shelfBreak",
        label="Shelf break bias",
        group="coasts",
        default=0.65,
        effect="Shallow-zone bias along distance→depth; higher = longer soft shelf.",
        in_game="Wider soft shelf → more we-shallows / we-shelf landforms and gentler OceanMap ramps.",
        up="Long continental shelves.",
        down="Shelf ends sooner; deeper water closer to shore.",
        kind="float",
        min_value=0.1,
        max_value=0.95,
        step=0.05,
    ),
    FieldMeta(
        key="shelfFalloff",
        label="Shelf falloff",
        group="coasts",
        default=2.2,
        effect="Power on soft distance→depth curve (higher = gentler).",
        in_game="Gentler curves feel like sandy shelves; lower power feels cliffier.",
        up="Softer bathymetry gradient.",
        down="Harder shelf edge.",
        kind="float",
        min_value=0.5,
        max_value=5.0,
        step=0.1,
    ),
    FieldMeta(
        key="shelfBlurSteps",
        label="Shelf blur passes",
        group="coasts",
        default=3,
        effect="Anti-alias passes on ocean elevation after shelf rewrite.",
        in_game="Smooths shelf artifacts so wet landforms don't stripe.",
        up="Smoother underwater contours.",
        down="More literal / noisier shelf.",
        kind="int",
        min_value=0,
        max_value=8,
        step=1,
    ),
    FieldMeta(
        key="noisyCoastlines",
        label="Noisy coastlines",
        group="coasts",
        default=0.045,
        effect="Mapgen4-style coast warp near sea level.",
        in_game="Breaks ruler-straight coasts into bays and headlands.",
        up="Ragged, island-friendly shores.",
        down="Smoother continental outlines.",
        kind="float",
        min_value=0.0,
        max_value=0.2,
        step=0.005,
    ),
    FieldMeta(
        key="shelfWidthNoise",
        label="Shelf width noise",
        group="coasts",
        default=0.45,
        effect="Alongshore variation in shelf width.",
        in_game="Some coasts get broad shallows, others pinch — more natural variety.",
        up="Strong shelf width variation.",
        down="Uniform shelf width.",
        kind="float",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
    ),
    FieldMeta(
        key="shelfDepthNoise",
        label="Shelf depth noise",
        group="coasts",
        default=0.4,
        effect="Alongshore noise on shelf depth.",
        in_game="Pockets of deeper/shallower water along the same coast.",
        up="More bathymetric texture.",
        down="Flatter shelf floor.",
        kind="float",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
    ),
    FieldMeta(
        key="shelfOceanDepth",
        label="Shelf ocean depth scale",
        group="coasts",
        default=1.4,
        effect="Scales how deep the shelf curve pushes open ocean.",
        in_game="Higher → deeper OceanMap / we-deepwet farther offshore.",
        up="Deeper open water.",
        down="Milder offshore depths.",
        kind="float",
        min_value=0.5,
        max_value=3.0,
        step=0.1,
    ),
    FieldMeta(
        key="shelfBlend",
        label="Shelf blend",
        group="coasts",
        default=0.5,
        effect="Blend soft shelf curve with residual platec bathymetry.",
        in_game="0 = pure shelf curve; 1 = keep more tectonic ocean trenches/rises.",
        up="More leftover platec ocean shape.",
        down="Cleaner designed shelf profile.",
        kind="float",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
    ),
    FieldMeta(
        key="oceanLevel",
        label="Ocean level",
        group="climate",
        default=1.0,
        effect="Elevation cutoff used as sea level during generation.",
        in_game="Higher → more ocean / less land; lower → larger continents.",
        up="Wetters world, more coastline.",
        down="More landmass.",
        kind="float",
        min_value=0.5,
        max_value=1.5,
        step=0.05,
    ),
    FieldMeta(
        key="blocksPerCell",
        label="Blocks per cell",
        group="pack",
        default=32,
        effect="Native-mode hint stored in the .vsplanet header.",
        in_game="Only matters if you switch the mod to native scale; Fit mode ignores it for sizing.",
        up="Coarser native sampling.",
        down="Finer native sampling.",
        kind="int",
        min_value=8,
        max_value=128,
        step=8,
    ),
    FieldMeta(
        key="tempMinC",
        label="Runtime temp min °C",
        group="runtime",
        default=-20.0,
        effect="Written into mod config: maps packed 0 → this °C.",
        in_game="Cold end of ClimateMap after normalize (or absolute WE) temperature.",
        up="Warmer 'coldest' biomes.",
        down="Harsher polar end.",
        kind="float",
        min_value=-50.0,
        max_value=10.0,
        step=1.0,
    ),
    FieldMeta(
        key="tempMaxC",
        label="Runtime temp max °C",
        group="runtime",
        default=40.0,
        effect="Written into mod config: maps packed 1 → this °C.",
        in_game="Hot end of ClimateMap.",
        up="Hotter tropics.",
        down="Milder hot end.",
        kind="float",
        min_value=10.0,
        max_value=60.0,
        step=1.0,
    ),
    FieldMeta(
        key="grayscaleHeightmap",
        label="Write grayscale heightmap",
        group="output",
        default=True,
        effect="Also writes <name>_grayscale.png beside other previews.",
        in_game="Preview only; not used by the VS mod.",
        up="Extra preview file.",
        down="Skip grayscale PNG.",
        kind="bool",
    ),
    FieldMeta(
        key="verbose",
        label="Verbose generation",
        group="output",
        default=True,
        effect="Prints WorldEngine progress to the log.",
        in_game="No gameplay effect.",
        up="More log detail.",
        down="Quieter log.",
        kind="bool",
    ),
)


META_BY_KEY = {m.key: m for m in FIELD_META}


@dataclass
class PlanetConfig:
    name: str = "example"
    seed: int = 69
    width: int = 2048
    height: int = 2048
    preset: str = "balanced"
    normalizeTemperature: bool = True
    numberOfPlates: int = 7
    foldingRatio: float = 0.06
    plateErosionPeriod: int = 90
    cycleCount: int = 3
    elevNoiseOctaves: int = 4
    elevNoiseAmp: float = 0.65
    elevBlurSteps: int = 2
    peakMix: float = 0.55
    peakSlope: float = 12.0
    shelfRadius: int = 0
    shelfShallow: float = 0.08
    shelfBreak: float = 0.65
    shelfFalloff: float = 2.2
    shelfBlurSteps: int = 3
    noisyCoastlines: float = 0.045
    shelfWidthNoise: float = 0.45
    shelfDepthNoise: float = 0.4
    shelfOceanDepth: float = 1.4
    shelfBlend: float = 0.5
    oceanLevel: float = 1.0
    blocksPerCell: int = 32
    tempMinC: float = -20.0
    tempMaxC: float = 40.0
    grayscaleHeightmap: bool = True
    verbose: bool = True
    outputDir: str = "output"
    planetFileName: str = "example.vsplanet"

    def planet_asset_name(self) -> str:
        # Default to example.vsplanet so ModConfig overlays (which almost always
        # keep PlanetAssetPath = worldengine:planets/example.vsplanet) still resolve.
        # World `name` is only for output folders / zip naming, not the in-mod asset id.
        base = self.planetFileName.strip() or "example"
        if not base.lower().endswith(".vsplanet"):
            base = f"{base}.vsplanet"
        return base

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanetConfig:
        known = {f.name for f in fields(cls)}
        cleaned = {k: v for k, v in data.items() if k in known}
        cfg = cls(**cleaned)
        cfg.validate()
        return cfg

    def validate(self) -> None:
        for meta in FIELD_META:
            if meta.key not in {f.name for f in fields(self)}:
                continue
            value = getattr(self, meta.key)
            if meta.kind == "choice" and meta.choices and value not in meta.choices:
                raise ValueError(f"{meta.key} must be one of {meta.choices}, got {value!r}")
            if meta.min_value is not None and isinstance(value, (int, float)) and value < meta.min_value:
                raise ValueError(f"{meta.key} below minimum {meta.min_value}")
            if meta.max_value is not None and isinstance(value, (int, float)) and value > meta.max_value:
                raise ValueError(f"{meta.key} above maximum {meta.max_value}")
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if self.width != self.height:
            # Allowed but discouraged; keep as warning-only at call site
            pass


def default_config() -> PlanetConfig:
    return PlanetConfig()


def iter_field_meta(group: str | None = None, easy_only: bool = False) -> Iterator[FieldMeta]:
    for meta in FIELD_META:
        if easy_only and not meta.easy:
            continue
        if group is not None and meta.group != group:
            continue
        yield meta


def load_preset(name: str) -> dict[str, Any]:
    path = _presets_dir() / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Preset not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Preset {name} must be a JSON object")
    return data


def list_presets() -> list[str]:
    d = _presets_dir()
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def apply_preset(cfg: PlanetConfig, preset_name: str) -> PlanetConfig:
    data = load_preset(preset_name)
    merged = cfg.to_dict()
    for key, value in data.items():
        if key in merged:
            merged[key] = value
    merged["preset"] = preset_name
    return PlanetConfig.from_dict(merged)


def load_config(path: Path | None = None) -> PlanetConfig:
    path = path or _default_planet_json()
    if not path.is_file():
        return default_config()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return PlanetConfig.from_dict(data)


def save_config(cfg: PlanetConfig, path: Path | None = None) -> None:
    path = path or _default_planet_json()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(cfg.to_dict(), f, indent=2)
        f.write("\n")


def parameters_markdown() -> str:
    lines = [
        "# Planet parameters",
        "",
        "Each control below explains **what changes in the generated maps** and **what you should expect in Vintage Story**.",
        "",
    ]
    current_group = None
    for meta in FIELD_META:
        if meta.group != current_group:
            current_group = meta.group
            lines.append(f"## {current_group.replace('_', ' ').title()}")
            lines.append("")
        lines.append(f"### `{meta.key}` — {meta.label}")
        lines.append("")
        lines.append(f"- **Default:** `{meta.default}`")
        if meta.min_value is not None or meta.max_value is not None:
            lines.append(f"- **Range:** {meta.min_value} … {meta.max_value}")
        lines.append(f"- **In the planet:** {meta.effect}")
        lines.append(f"- **In Vintage Story:** {meta.in_game}")
        lines.append(f"- **Turn up:** {meta.up}")
        lines.append(f"- **Turn down:** {meta.down}")
        lines.append("")
    return "\n".join(lines)


def clone_defaults_with_overrides(**overrides: Any) -> dict[str, Any]:
    data = default_config().to_dict()
    data.update(overrides)
    return data
