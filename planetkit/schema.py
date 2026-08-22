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
        effect="Names output files and folders for this planet.",
        in_game="Does not change gameplay; only file and folder names.",
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
        effect="Controls the random layout of continents and climate.",
        in_game="Same seed and settings always produce the same planet.",
        up="A new seed gives a different world layout.",
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
        effect="Horizontal resolution of the planet grid. Larger maps take longer to generate.",
        in_game="With Fit scale, the planet stretches across the Vintage Story map; more cells mean finer coasts.",
        up="More detail, slower generation, larger planet file.",
        down="Faster generation; coasts look coarser when stretched.",
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
        in_game="Match width for a square map unless you want a stretched rectangle.",
        up="More detail; slower generation.",
        down="Faster; coarser detail.",
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
        effect="Applies a starting set of generation settings (plates, coasts, peaks, and so on).",
        in_game="A quick starting point; you can still change Advanced settings afterward.",
        up="Choose the style you want, then fine-tune.",
        down="—",
        kind="choice",
        choices=("balanced", "continental", "archipelago"),
        easy=True,
    ),
    FieldMeta(
        key="distanceToSun",
        label="Distance to sun",
        group="easy",
        default=1.0,
        effect="Overall heat bias of the planet (1.0 ≈ Earth). With Climate extremes, sets where the °C window sits.",
        in_game="Closer shifts climates hotter; farther shifts them colder. Extremes still controls how wide that band is.",
        up="Farther from the sun; colder band (narrow extremes stay cold).",
        down="Closer to the sun; hotter band (narrow extremes stay hot).",
        kind="float",
        min_value=0.7,
        max_value=1.3,
        step=0.01,
        easy=True,
    ),
    FieldMeta(
        key="axialTilt",
        label="Axial tilt",
        group="easy",
        default=0.0,
        effect="Shifts the hot band away from the equator (0 ≈ Earth-like).",
        in_game="Moves where the tropics and poles sit on the map.",
        up="Hot band moves toward one pole.",
        down="Hot band moves toward the other pole, or back to the equator.",
        kind="float",
        min_value=-0.15,
        max_value=0.15,
        step=0.01,
        easy=True,
    ),
    FieldMeta(
        key="climateExtremes",
        label="Climate extremes",
        group="easy",
        default=0.5,
        effect="Width of the °C window around the sun-distance heat bias. Middle at Earth orbit ≈ −20…40 °C.",
        in_game="Narrow keeps climates near that bias (hot planet stays hot; cold stays cold). Wide still spans harsh poles and tropics.",
        up="Wider °C range around the orbit bias.",
        down="Narrower °C band toward the orbit bias (hot→hotter band, cold→colder band).",
        kind="float",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        easy=True,
    ),
    FieldMeta(
        key="precipGamma",
        label="Precipitation (wet/dry)",
        group="easy",
        default=1.25,
        effect="How strongly cold land dries out. Higher values make cold regions drier.",
        in_game="Changes wet and dry biomes; does not set the °C range.",
        up="Drier cold regions; stronger wet–dry contrast.",
        down="More even moisture; cold land stays wetter.",
        kind="float",
        min_value=0.5,
        max_value=3.0,
        step=0.05,
        easy=True,
    ),
    FieldMeta(
        key="precipGammaOffset",
        label="Precipitation gamma offset",
        group="climate",
        default=0.2,
        effect="Minimum moisture left after the wet/dry curve, so poles are not forced bone-dry.",
        in_game="Higher keeps a bit of moisture even in very dry cold areas.",
        up="Less bone-dry poles.",
        down="Allows drier cold extremes.",
        kind="float",
        min_value=0.0,
        max_value=0.5,
        step=0.05,
        easy=False,
    ),
    FieldMeta(
        key="numberOfPlates",
        label="Number of plates",
        group="tectonics",
        default=7,
        effect="How many tectonic plates shape the continents.",
        in_game="More plates mean broken coasts and island chains; fewer mean larger landmasses.",
        up="More islands and fragmented continents.",
        down="Bigger, simpler continents.",
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
        effect="How strongly colliding plates push up mountains.",
        in_game="Stronger folding makes taller, sharper mountain belts along plate edges.",
        up="Taller, sharper ranges.",
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
        effect="How much tectonic erosion rounds the landscape during generation (higher = more worn).",
        in_game="Higher values look older and softer; lower values look sharper and younger.",
        up="More rounded, mature relief.",
        down="Rougher, less worn uplift.",
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
        effect="How many tectonic simulation passes to run.",
        in_game="More cycles further develop coasts and mountain belts (and take longer).",
        up="More developed tectonics; slower.",
        down="Faster; simpler plate layout.",
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
        effect="Layers of fine elevation noise on top of tectonic shape.",
        in_game="Adds small hills and surface texture instead of flat tectonic slabs.",
        up="Richer local roughness.",
        down="Smoother, more slab-like land.",
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
        effect="Strength of fine elevation noise relative to tectonic height.",
        in_game="Higher makes bumpier interiors and more irregular coasts.",
        up="Craggier, more irregular terrain.",
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
        effect="Smoothing passes on height before land and ocean are classified.",
        in_game="Softens jagged height noise; too much can blur sharp ridges.",
        up="Smoother height.",
        down="Crisper, possibly noisier relief.",
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
        effect="How strongly plate-boundary mountains are boosted.",
        in_game="Controls how much mountain belts stand above the surrounding land.",
        up="More dramatic ranges and highlands.",
        down="Flatter continents; mountains less distinct.",
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
        effect="How quickly mountain boost falls off with distance from plate boundaries.",
        in_game="Higher keeps peaks narrow; lower makes wide highland shoulders.",
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
        effect="Continental shelf width in cells. 0 picks a width automatically from map size.",
        in_game="How wide the shallow nearshore band is before deep ocean.",
        up="Wider shelves and longer shallows.",
        down="0 uses auto width; small values pinch the shelf.",
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
        effect="How shallow water stays right next to the coast on the shelf curve.",
        in_game="Keeps water just offshore from dropping to deep sea too quickly.",
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
        effect="How far the soft shallow shelf extends before deeper water.",
        in_game="Wider soft shelves mean more shallow nearshore water and gentler depth change offshore.",
        up="Longer continental shelves.",
        down="Shelf ends sooner; deep water closer to shore.",
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
        effect="How gently depth increases across the shelf (higher = gentler).",
        in_game="Gentler shelves feel sandy; lower values feel more cliff-like.",
        up="Softer depth gradient.",
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
        effect="Smoothing passes on ocean depth after the shelf is applied.",
        in_game="Smooths underwater contours so shallow bands look less striped.",
        up="Smoother underwater contours.",
        down="More literal, noisier shelf.",
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
        effect="Warps the coastline near sea level to break straight edges.",
        in_game="Turns ruler-straight coasts into bays and headlands.",
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
        effect="How much shelf width varies along the coast.",
        in_game="Some coasts get broad shallows; others pinch in.",
        up="Stronger shelf width variation.",
        down="More uniform shelf width.",
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
        effect="How much shelf depth varies along the coast.",
        in_game="Pockets of deeper or shallower water along the same shore.",
        up="More uneven seafloor near shore.",
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
        effect="How deep open ocean becomes beyond the shelf.",
        in_game="Higher means deeper water farther offshore.",
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
        effect="Mix between the smooth shelf curve and leftover tectonic seafloor shape.",
        in_game="0 is a clean designed shelf; 1 keeps more trenches and rises from tectonics.",
        up="More leftover tectonic ocean shape.",
        down="Cleaner designed shelf profile.",
        kind="float",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
    ),
    FieldMeta(
        key="oceanLevel",
        label="Ocean level",
        group="easy",
        default=1.0,
        effect="Sea level used while generating the planet.",
        in_game="Higher means more ocean and less land; lower means larger continents.",
        up="More ocean and coastline.",
        down="More landmass.",
        kind="float",
        min_value=0.5,
        max_value=1.5,
        step=0.05,
        easy=True,
    ),
    FieldMeta(
        key="blocksPerCell",
        label="Blocks per cell",
        group="pack",
        default=32,
        effect="Native-scale hint stored in the planet file header.",
        in_game="Only matters if the mod uses native scale; Fit mode ignores it for world size.",
        up="Coarser native sampling.",
        down="Finer native sampling.",
        kind="int",
        min_value=8,
        max_value=128,
        step=8,
    ),
    FieldMeta(
        key="tempMinC",
        label="Coldest climate °C",
        group="runtime",
        default=-20.0,
        effect="Cold end of the in-game °C window (Easy sets this from sun distance + Climate extremes).",
        in_game="Cold end of the climate map.",
        up="Warmer coldest biomes.",
        down="Harsher polar climates.",
        kind="float",
        min_value=-50.0,
        max_value=40.0,
        step=1.0,
        easy=False,
    ),
    FieldMeta(
        key="tempMaxC",
        label="Hottest climate °C",
        group="runtime",
        default=40.0,
        effect="Hot end of the in-game °C window (Easy sets this from sun distance + Climate extremes).",
        in_game="Hot end of the climate map.",
        up="Hotter tropics.",
        down="Milder hot climates.",
        kind="float",
        min_value=-20.0,
        max_value=60.0,
        step=1.0,
        easy=False,
    ),
    FieldMeta(
        key="grayscaleHeightmap",
        label="Write grayscale heightmap",
        group="output",
        default=True,
        effect="Also writes a grayscale height preview next to the other images.",
        in_game="Preview only; not used by the game.",
        up="Extra preview file.",
        down="Skip the grayscale image.",
        kind="bool",
    ),
    FieldMeta(
        key="verbose",
        label="Verbose generation",
        group="output",
        default=True,
        effect="Writes detailed generation progress to the log.",
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
    distanceToSun: float = 1.0
    axialTilt: float = 0.0
    climateExtremes: float = 0.5
    precipGamma: float = 1.25
    precipGammaOffset: float = 0.2
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
        # In-mod asset id (default example.vsplanet); world `name` is for output folders/zips only.
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
        field_names = {f.name for f in fields(self)}
        for meta in FIELD_META:
            if meta.key not in field_names:
                continue
            value = getattr(self, meta.key)
            label = meta.label
            if meta.kind == "choice" and meta.choices and value not in meta.choices:
                choices = ", ".join(meta.choices)
                raise ValueError(f"{label} must be one of: {choices} (got {value!r})")
            if meta.kind == "int" and not isinstance(value, bool) and isinstance(value, float) and not float(value).is_integer():
                raise ValueError(f"{label} must be a whole number (got {value})")
            if meta.kind in ("int", "float") and not isinstance(value, bool):
                if not isinstance(value, (int, float)):
                    raise ValueError(f"{label} must be a number (got {value!r})")
                if meta.min_value is not None and value < meta.min_value:
                    raise ValueError(f"{label} below minimum value of {meta.min_value}")
                if meta.max_value is not None and value > meta.max_value:
                    raise ValueError(f"{label} above maximum value of {meta.max_value}")
            if meta.kind == "str" and meta.key == "name":
                text = str(value).strip()
                if not text:
                    raise ValueError("World name must not be empty")
                bad = [c for c in text if not (c.isalnum() or c in ("-", "_"))]
                if bad:
                    raise ValueError(
                        "World name may only use letters, numbers, hyphens, and underscores "
                        f"(remove {''.join(sorted(set(bad)))!r})"
                    )
        if not str(self.name).strip():
            raise ValueError("World name must not be empty")
        if float(self.tempMinC) >= float(self.tempMaxC):
            raise ValueError(
                f"Coldest climate °C ({self.tempMinC}) must be less than "
                f"Hottest climate °C ({self.tempMaxC})"
            )
        # Guard against pathological map sizes even if metadata is bypassed.
        for dim_name, dim in (("Width (cells)", self.width), ("Height (cells)", self.height)):
            if not isinstance(dim, int) or isinstance(dim, bool):
                raise ValueError(f"{dim_name} must be a whole number")
            if dim < 256:
                raise ValueError(f"{dim_name} below minimum value of 256")
            if dim > 4096:
                raise ValueError(f"{dim_name} above maximum value of 4096")


def parse_field_value(meta: FieldMeta, raw: Any) -> Any:
    """Coerce a UI/CLI raw value using field metadata; raise ValueError with label."""
    label = meta.label
    if meta.kind == "bool":
        if isinstance(raw, bool):
            return raw
        text = str(raw).strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off"):
            return False
        raise ValueError(f"{label} must be true or false (got {raw!r})")
    if meta.kind == "int":
        text = str(raw).strip()
        if text == "":
            raise ValueError(f"{label} is required")
        try:
            # Accept "3.0" but reject "3.2"
            as_float = float(text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be a whole number (got {raw!r})") from exc
        if not as_float.is_integer():
            raise ValueError(f"{label} must be a whole number (got {raw!r})")
        return int(as_float)
    if meta.kind == "float":
        text = str(raw).strip()
        if text == "":
            raise ValueError(f"{label} is required")
        try:
            return float(text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be a number (got {raw!r})") from exc
    if meta.kind == "choice":
        text = str(raw).strip()
        if meta.choices and text not in meta.choices:
            choices = ", ".join(meta.choices)
            raise ValueError(f"{label} must be one of: {choices} (got {raw!r})")
        return text
    return str(raw).strip() if raw is not None else ""


def default_config() -> PlanetConfig:
    return PlanetConfig()


def climate_window_from_extremes(
    extremes: float,
    distance_to_sun: float = 1.0,
) -> tuple[float, float]:
    """
    Build (tempMinC, tempMaxC) from Easy climate controls.

    - climateExtremes sets the *width* of the °C window (half-span 10…50).
    - distanceToSun shifts the *center* of that window (Earth 1.0 → 10 °C;
      closer → hotter center; farther → colder center).

    Mid extremes at Earth orbit still yields ≈ −20…40 °C.
    """
    t = max(0.0, min(1.0, float(extremes)))
    half = 10.0 + t * 40.0  # 10…50

    # distance 0.7 → +1 heat, 1.0 → 0, 1.3 → −1
    dist = max(0.7, min(1.3, float(distance_to_sun)))
    heat = (1.0 - dist) / 0.3
    center = 10.0 + heat * 25.0  # 35 °C closest … −15 °C farthest

    lo = center - half
    hi = center + half
    # Keep within a sensible Vintage Story climate span.
    lo = max(-50.0, min(40.0, lo))
    hi = max(-20.0, min(60.0, hi))
    if hi <= lo + 5.0:
        mid = 0.5 * (lo + hi)
        lo, hi = mid - 2.5, mid + 2.5
    return lo, hi


def apply_climate_extremes(cfg: PlanetConfig) -> PlanetConfig:
    """Write tempMinC/tempMaxC from sun distance + Climate extremes (Easy controls)."""
    lo, hi = climate_window_from_extremes(cfg.climateExtremes, cfg.distanceToSun)
    cfg.tempMinC = lo
    cfg.tempMaxC = hi
    return cfg


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
