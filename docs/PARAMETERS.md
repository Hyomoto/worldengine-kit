# Planet parameters

Each control below explains **what changes in the generated maps** and **what you should expect in Vintage Story**.

## Easy

### `name` — World name

- **Default:** `example`
- **In the planet:** Sets output file names (.world, previews, .vsplanet, mod zip).
- **In Vintage Story:** Only affects asset naming inside the mod zip.
- **Turn up:** Use a short lowercase id without spaces.
- **Turn down:** —

### `seed` — Seed

- **Default:** `69`
- **Range:** 0 … 2147483647
- **In the planet:** Initializes all procedural noise and plate layout.
- **In Vintage Story:** Same seed + same settings → same planet. Change seed for a new layout.
- **Turn up:** Different continents and climates.
- **Turn down:** —

### `width` — Width (cells)

- **Default:** `2048`
- **Range:** 256 … 4096
- **In the planet:** Horizontal resolution of the planet grid. Larger maps take much longer.
- **In Vintage Story:** With Fit scale, the whole planet stretches over the VS map. More cells = finer coasts before stretch.
- **Turn up:** More detail, slower generation, larger .vsplanet.
- **Turn down:** Faster; coasts look coarser when stretched to a large world.

### `height` — Height (cells)

- **Default:** `2048`
- **Range:** 256 … 4096
- **In the planet:** Vertical resolution of the planet grid.
- **In Vintage Story:** Same as width for Fit mode; prefer square maps unless you know you want stretch.
- **Turn up:** More detail / slower.
- **Turn down:** Faster / coarser.

### `preset` — Style preset

- **Default:** `balanced`
- **In the planet:** Loads a named bundle of generation knobs (plates, shelf, peaks, etc.).
- **In Vintage Story:** Quick starting point; you can still tweak advanced fields afterward.
- **Turn up:** Pick the outcome you want, then fine-tune.
- **Turn down:** —

### `normalizeTemperature` — Normalize temperature

- **Default:** `True`
- **In the planet:** At pack time, stretches land temperature onto [0,1] from that planet's land min–max.
- **In Vintage Story:** ON (default): VS sees the full −20…40 °C spectrum so all biomes can appear. OFF: a cold WE orbit stays cold.
- **Turn up:** Full biome spectrum from whatever WE produced.
- **Turn down:** Preserve absolute WE cold/hot bias (intentionally harsh climates).

## Tectonics

### `numberOfPlates` — Number of plates

- **Default:** `7`
- **Range:** 3 … 20
- **In the planet:** How many tectonic plates compete during platec simulation.
- **In Vintage Story:** More plates → more fragmented continents and island chains; fewer → larger landmasses.
- **Turn up:** Archipelagos, broken coasts, more plate-boundary mountains.
- **Turn down:** Big continents, simpler coast outlines.

### `foldingRatio` — Folding ratio

- **Default:** `0.06`
- **Range:** 0.0 … 0.3
- **In the planet:** Platec orogeny strength when plates collide.
- **In Vintage Story:** Stronger folding → taller / sharper mountain belts along plate edges.
- **Turn up:** Younger, punchier ranges.
- **Turn down:** Gentler hills; mountains less dominant.

### `plateErosionPeriod` — Plate erosion period

- **Default:** `90`
- **Range:** 10 … 200
- **In the planet:** Tectonic erosion interval inside platec (higher = more mature landscape).
- **In Vintage Story:** Higher values wear sharp uplift into softer, older-looking terrain.
- **Turn up:** More mature / rounded relief.
- **Turn down:** Rougher, less eroded uplift.

### `cycleCount` — Simulation cycles

- **Default:** `3`
- **Range:** 1 … 8
- **In the planet:** How many platec simulation cycles to run.
- **In Vintage Story:** More cycles deepen plate interaction (coasts and ranges evolve further).
- **Turn up:** More developed tectonics (slower).
- **Turn down:** Faster, simpler plate layout.

## Relief

### `elevNoiseOctaves` — Elevation noise octaves

- **Default:** `4`
- **Range:** 0 … 8
- **In the planet:** Simplex octaves added on top of plate elevation.
- **In Vintage Story:** Adds fine hills and texture instead of pure tectonic slabs.
- **Turn up:** Richer local roughness.
- **Turn down:** Smoother, more 'plate-only' land.

### `elevNoiseAmp` — Elevation noise amplitude

- **Default:** `0.65`
- **Range:** 0.0 … 2.0
- **In the planet:** Strength of elevation noise relative to plate heights.
- **In Vintage Story:** Higher → bumpier interiors and noisier coastlines before shelf rewrite.
- **Turn up:** Craggy / irregular terrain.
- **Turn down:** Cleaner large-scale shapes.

### `elevBlurSteps` — Elevation blur passes

- **Default:** `2`
- **Range:** 0 … 8
- **In the planet:** Anti-alias passes on elevation before ocean classification.
- **In Vintage Story:** Softens jagged height artifacts; too much can melt sharp ridges.
- **Turn up:** Smoother heightfields.
- **Turn down:** Crisper (possibly noisier) relief.

### `peakMix` — Peak mix

- **Default:** `0.55`
- **Range:** 0.0 … 1.0
- **In the planet:** Weight of plate-boundary mountain boost.
- **In Vintage Story:** How strongly mountain belts punch above surrounding land.
- **Turn up:** Dramatic ranges / highland belts.
- **Turn down:** Flatter continents; mountains less special.

### `peakSlope` — Peak slope

- **Default:** `12.0`
- **Range:** 1.0 … 40.0
- **In the planet:** Distance-field falloff for mountain boost.
- **In Vintage Story:** Higher → peaks stay narrow; lower → wide highland shoulders.
- **Turn up:** Narrower mountain spines.
- **Turn down:** Broader elevated regions.

## Coasts

### `shelfRadius` — Shelf radius

- **Default:** `0`
- **Range:** 0 … 128
- **In the planet:** Continental shelf width in cells; 0 = auto from map size (~24 at 1024).
- **In Vintage Story:** Controls how wide the soft nearshore bathymetry band is before deep ocean.
- **Turn up:** Wider shelves / longer shallows (explicit cell count).
- **Turn down:** 0 keeps auto scaling; small values pinch the shelf.

### `shelfShallow` — Shelf shallow floor

- **Default:** `0.08`
- **Range:** 0.0 … 0.5
- **In the planet:** Near-coast relative depth floor on the soft shelf curve.
- **In Vintage Story:** Keeps immediate offshore water from snapping to deep marine too soon.
- **Turn up:** Shallower nearshore flats.
- **Turn down:** Steeper drop just off the beach.

### `shelfBreak` — Shelf break bias

- **Default:** `0.65`
- **Range:** 0.1 … 0.95
- **In the planet:** Shallow-zone bias along distance→depth; higher = longer soft shelf.
- **In Vintage Story:** Wider soft shelf → more we-shallows / we-shelf landforms and gentler OceanMap ramps.
- **Turn up:** Long continental shelves.
- **Turn down:** Shelf ends sooner; deeper water closer to shore.

### `shelfFalloff` — Shelf falloff

- **Default:** `2.2`
- **Range:** 0.5 … 5.0
- **In the planet:** Power on soft distance→depth curve (higher = gentler).
- **In Vintage Story:** Gentler curves feel like sandy shelves; lower power feels cliffier.
- **Turn up:** Softer bathymetry gradient.
- **Turn down:** Harder shelf edge.

### `shelfBlurSteps` — Shelf blur passes

- **Default:** `3`
- **Range:** 0 … 8
- **In the planet:** Anti-alias passes on ocean elevation after shelf rewrite.
- **In Vintage Story:** Smooths shelf artifacts so wet landforms don't stripe.
- **Turn up:** Smoother underwater contours.
- **Turn down:** More literal / noisier shelf.

### `noisyCoastlines` — Noisy coastlines

- **Default:** `0.045`
- **Range:** 0.0 … 0.2
- **In the planet:** Mapgen4-style coast warp near sea level.
- **In Vintage Story:** Breaks ruler-straight coasts into bays and headlands.
- **Turn up:** Ragged, island-friendly shores.
- **Turn down:** Smoother continental outlines.

### `shelfWidthNoise` — Shelf width noise

- **Default:** `0.45`
- **Range:** 0.0 … 1.0
- **In the planet:** Alongshore variation in shelf width.
- **In Vintage Story:** Some coasts get broad shallows, others pinch — more natural variety.
- **Turn up:** Strong shelf width variation.
- **Turn down:** Uniform shelf width.

### `shelfDepthNoise` — Shelf depth noise

- **Default:** `0.4`
- **Range:** 0.0 … 1.0
- **In the planet:** Alongshore noise on shelf depth.
- **In Vintage Story:** Pockets of deeper/shallower water along the same coast.
- **Turn up:** More bathymetric texture.
- **Turn down:** Flatter shelf floor.

### `shelfOceanDepth` — Shelf ocean depth scale

- **Default:** `1.4`
- **Range:** 0.5 … 3.0
- **In the planet:** Scales how deep the shelf curve pushes open ocean.
- **In Vintage Story:** Higher → deeper OceanMap / we-deepwet farther offshore.
- **Turn up:** Deeper open water.
- **Turn down:** Milder offshore depths.

### `shelfBlend` — Shelf blend

- **Default:** `0.5`
- **Range:** 0.0 … 1.0
- **In the planet:** Blend soft shelf curve with residual platec bathymetry.
- **In Vintage Story:** 0 = pure shelf curve; 1 = keep more tectonic ocean trenches/rises.
- **Turn up:** More leftover platec ocean shape.
- **Turn down:** Cleaner designed shelf profile.

## Climate

### `oceanLevel` — Ocean level

- **Default:** `1.0`
- **Range:** 0.5 … 1.5
- **In the planet:** Elevation cutoff used as sea level during generation.
- **In Vintage Story:** Higher → more ocean / less land; lower → larger continents.
- **Turn up:** Wetters world, more coastline.
- **Turn down:** More landmass.

## Pack

### `blocksPerCell` — Blocks per cell

- **Default:** `32`
- **Range:** 8 … 128
- **In the planet:** Native-mode hint stored in the .vsplanet header.
- **In Vintage Story:** Only matters if you switch the mod to native scale; Fit mode ignores it for sizing.
- **Turn up:** Coarser native sampling.
- **Turn down:** Finer native sampling.

## Runtime

### `tempMinC` — Runtime temp min °C

- **Default:** `-20.0`
- **Range:** -50.0 … 10.0
- **In the planet:** Written into mod config: maps packed 0 → this °C.
- **In Vintage Story:** Cold end of ClimateMap after normalize (or absolute WE) temperature.
- **Turn up:** Warmer 'coldest' biomes.
- **Turn down:** Harsher polar end.

### `tempMaxC` — Runtime temp max °C

- **Default:** `40.0`
- **Range:** 10.0 … 60.0
- **In the planet:** Written into mod config: maps packed 1 → this °C.
- **In Vintage Story:** Hot end of ClimateMap.
- **Turn up:** Hotter tropics.
- **Turn down:** Milder hot end.

## Output

### `grayscaleHeightmap` — Write grayscale heightmap

- **Default:** `True`
- **In the planet:** Also writes <name>_grayscale.png beside other previews.
- **In Vintage Story:** Preview only; not used by the VS mod.
- **Turn up:** Extra preview file.
- **Turn down:** Skip grayscale PNG.

### `verbose` — Verbose generation

- **Default:** `True`
- **In the planet:** Prints WorldEngine progress to the log.
- **In Vintage Story:** No gameplay effect.
- **Turn up:** More log detail.
- **Turn down:** Quieter log.
