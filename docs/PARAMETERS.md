# Planet parameters

Each control below explains **what changes in the generated maps** and **what you should expect in Vintage Story**.

## Easy

### `name` — World name

- **Default:** `example`
- **In the planet:** Names output files and folders for this planet.
- **In Vintage Story:** Does not change gameplay; only file and folder names.
- **Turn up:** Use a short lowercase id without spaces.
- **Turn down:** —

### `seed` — Seed

- **Default:** `69`
- **Range:** 0 … 2147483647
- **In the planet:** Controls the random layout of continents and climate.
- **In Vintage Story:** Same seed and settings always produce the same planet.
- **Turn up:** A new seed gives a different world layout.
- **Turn down:** —

### `width` — Width (cells)

- **Default:** `2048`
- **Range:** 256 … 4096
- **In the planet:** Horizontal resolution of the planet grid. Larger maps take longer to generate.
- **In Vintage Story:** With Fit scale, the planet stretches across the Vintage Story map; more cells mean finer coasts.
- **Turn up:** More detail, slower generation, larger planet file.
- **Turn down:** Faster generation; coasts look coarser when stretched.

### `height` — Height (cells)

- **Default:** `2048`
- **Range:** 256 … 4096
- **In the planet:** Vertical resolution of the planet grid.
- **In Vintage Story:** Match width for a square map unless you want a stretched rectangle.
- **Turn up:** More detail; slower generation.
- **Turn down:** Faster; coarser detail.

### `preset` — Style preset

- **Default:** `balanced`
- **In the planet:** Applies a starting set of generation settings (plates, coasts, peaks, and so on).
- **In Vintage Story:** A quick starting point; you can still change Advanced settings afterward.
- **Turn up:** Choose the style you want, then fine-tune.
- **Turn down:** —

### `distanceToSun` — Distance to sun

- **Default:** `1.0`
- **Range:** 0.7 … 1.3
- **In the planet:** Overall heat bias of the planet (1.0 ≈ Earth). With Climate extremes, sets where the °C window sits.
- **In Vintage Story:** Closer shifts climates hotter; farther shifts them colder. Extremes still controls how wide that band is.
- **Turn up:** Farther from the sun; colder band (narrow extremes stay cold).
- **Turn down:** Closer to the sun; hotter band (narrow extremes stay hot).

### `axialTilt` — Axial tilt

- **Default:** `0.0`
- **Range:** -0.15 … 0.15
- **In the planet:** Shifts the hot band away from the equator (0 ≈ Earth-like).
- **In Vintage Story:** Moves where the tropics and poles sit on the map.
- **Turn up:** Hot band moves toward one pole.
- **Turn down:** Hot band moves toward the other pole, or back to the equator.

### `climateExtremes` — Climate extremes

- **Default:** `0.5`
- **Range:** 0.0 … 1.0
- **In the planet:** Width of the °C window around the sun-distance heat bias. Middle at Earth orbit ≈ −20…40 °C.
- **In Vintage Story:** Narrow keeps climates near that bias (hot planet stays hot; cold stays cold). Wide still spans harsh poles and tropics.
- **Turn up:** Wider °C range around the orbit bias.
- **Turn down:** Narrower °C band toward the orbit bias (hot→hotter band, cold→colder band).

### `precipGamma` — Precipitation (wet/dry)

- **Default:** `1.25`
- **Range:** 0.5 … 3.0
- **In the planet:** How strongly cold land dries out. Higher values make cold regions drier.
- **In Vintage Story:** Changes wet and dry biomes; does not set the °C range.
- **Turn up:** Drier cold regions; stronger wet–dry contrast.
- **Turn down:** More even moisture; cold land stays wetter.

## Climate

### `precipGammaOffset` — Precipitation gamma offset

- **Default:** `0.2`
- **Range:** 0.0 … 0.5
- **In the planet:** Minimum moisture left after the wet/dry curve, so poles are not forced bone-dry.
- **In Vintage Story:** Higher keeps a bit of moisture even in very dry cold areas.
- **Turn up:** Less bone-dry poles.
- **Turn down:** Allows drier cold extremes.

## Tectonics

### `numberOfPlates` — Number of plates

- **Default:** `7`
- **Range:** 3 … 20
- **In the planet:** How many tectonic plates shape the continents.
- **In Vintage Story:** More plates mean broken coasts and island chains; fewer mean larger landmasses.
- **Turn up:** More islands and fragmented continents.
- **Turn down:** Bigger, simpler continents.

### `foldingRatio` — Folding ratio

- **Default:** `0.06`
- **Range:** 0.0 … 0.3
- **In the planet:** How strongly colliding plates push up mountains.
- **In Vintage Story:** Stronger folding makes taller, sharper mountain belts along plate edges.
- **Turn up:** Taller, sharper ranges.
- **Turn down:** Gentler hills; mountains less dominant.

### `plateErosionPeriod` — Plate erosion period

- **Default:** `90`
- **Range:** 10 … 200
- **In the planet:** How much tectonic erosion rounds the landscape during generation (higher = more worn).
- **In Vintage Story:** Higher values look older and softer; lower values look sharper and younger.
- **Turn up:** More rounded, mature relief.
- **Turn down:** Rougher, less worn uplift.

### `cycleCount` — Simulation cycles

- **Default:** `3`
- **Range:** 1 … 8
- **In the planet:** How many tectonic simulation passes to run.
- **In Vintage Story:** More cycles further develop coasts and mountain belts (and take longer).
- **Turn up:** More developed tectonics; slower.
- **Turn down:** Faster; simpler plate layout.

## Relief

### `elevNoiseOctaves` — Elevation noise octaves

- **Default:** `4`
- **Range:** 0 … 8
- **In the planet:** Layers of fine elevation noise on top of tectonic shape.
- **In Vintage Story:** Adds small hills and surface texture instead of flat tectonic slabs.
- **Turn up:** Richer local roughness.
- **Turn down:** Smoother, more slab-like land.

### `elevNoiseAmp` — Elevation noise amplitude

- **Default:** `0.65`
- **Range:** 0.0 … 2.0
- **In the planet:** Strength of fine elevation noise relative to tectonic height.
- **In Vintage Story:** Higher makes bumpier interiors and more irregular coasts.
- **Turn up:** Craggier, more irregular terrain.
- **Turn down:** Cleaner large-scale shapes.

### `elevBlurSteps` — Elevation blur passes

- **Default:** `2`
- **Range:** 0 … 8
- **In the planet:** Smoothing passes on height before land and ocean are classified.
- **In Vintage Story:** Softens jagged height noise; too much can blur sharp ridges.
- **Turn up:** Smoother height.
- **Turn down:** Crisper, possibly noisier relief.

### `peakMix` — Peak mix

- **Default:** `0.55`
- **Range:** 0.0 … 1.0
- **In the planet:** How strongly plate-boundary mountains are boosted.
- **In Vintage Story:** Controls how much mountain belts stand above the surrounding land.
- **Turn up:** More dramatic ranges and highlands.
- **Turn down:** Flatter continents; mountains less distinct.

### `peakSlope` — Peak slope

- **Default:** `12.0`
- **Range:** 1.0 … 40.0
- **In the planet:** How quickly mountain boost falls off with distance from plate boundaries.
- **In Vintage Story:** Higher keeps peaks narrow; lower makes wide highland shoulders.
- **Turn up:** Narrower mountain spines.
- **Turn down:** Broader elevated regions.

## Coasts

### `shelfRadius` — Shelf radius

- **Default:** `0`
- **Range:** 0 … 128
- **In the planet:** Continental shelf width in cells. 0 picks a width automatically from map size.
- **In Vintage Story:** How wide the shallow nearshore band is before deep ocean.
- **Turn up:** Wider shelves and longer shallows.
- **Turn down:** 0 uses auto width; small values pinch the shelf.

### `shelfShallow` — Shelf shallow floor

- **Default:** `0.08`
- **Range:** 0.0 … 0.5
- **In the planet:** How shallow water stays right next to the coast on the shelf curve.
- **In Vintage Story:** Keeps water just offshore from dropping to deep sea too quickly.
- **Turn up:** Shallower nearshore flats.
- **Turn down:** Steeper drop just off the beach.

### `shelfBreak` — Shelf break bias

- **Default:** `0.65`
- **Range:** 0.1 … 0.95
- **In the planet:** How far the soft shallow shelf extends before deeper water.
- **In Vintage Story:** Wider soft shelves mean more shallow nearshore water and gentler depth change offshore.
- **Turn up:** Longer continental shelves.
- **Turn down:** Shelf ends sooner; deep water closer to shore.

### `shelfFalloff` — Shelf falloff

- **Default:** `2.2`
- **Range:** 0.5 … 5.0
- **In the planet:** How gently depth increases across the shelf (higher = gentler).
- **In Vintage Story:** Gentler shelves feel sandy; lower values feel more cliff-like.
- **Turn up:** Softer depth gradient.
- **Turn down:** Harder shelf edge.

### `shelfBlurSteps` — Shelf blur passes

- **Default:** `3`
- **Range:** 0 … 8
- **In the planet:** Smoothing passes on ocean depth after the shelf is applied.
- **In Vintage Story:** Smooths underwater contours so shallow bands look less striped.
- **Turn up:** Smoother underwater contours.
- **Turn down:** More literal, noisier shelf.

### `noisyCoastlines` — Noisy coastlines

- **Default:** `0.045`
- **Range:** 0.0 … 0.2
- **In the planet:** Warps the coastline near sea level to break straight edges.
- **In Vintage Story:** Turns ruler-straight coasts into bays and headlands.
- **Turn up:** Ragged, island-friendly shores.
- **Turn down:** Smoother continental outlines.

### `shelfWidthNoise` — Shelf width noise

- **Default:** `0.45`
- **Range:** 0.0 … 1.0
- **In the planet:** How much shelf width varies along the coast.
- **In Vintage Story:** Some coasts get broad shallows; others pinch in.
- **Turn up:** Stronger shelf width variation.
- **Turn down:** More uniform shelf width.

### `shelfDepthNoise` — Shelf depth noise

- **Default:** `0.4`
- **Range:** 0.0 … 1.0
- **In the planet:** How much shelf depth varies along the coast.
- **In Vintage Story:** Pockets of deeper or shallower water along the same shore.
- **Turn up:** More uneven seafloor near shore.
- **Turn down:** Flatter shelf floor.

### `shelfOceanDepth` — Shelf ocean depth scale

- **Default:** `1.4`
- **Range:** 0.5 … 3.0
- **In the planet:** How deep open ocean becomes beyond the shelf.
- **In Vintage Story:** Higher means deeper water farther offshore.
- **Turn up:** Deeper open water.
- **Turn down:** Milder offshore depths.

### `shelfBlend` — Shelf blend

- **Default:** `0.5`
- **Range:** 0.0 … 1.0
- **In the planet:** Mix between the smooth shelf curve and leftover tectonic seafloor shape.
- **In Vintage Story:** 0 is a clean designed shelf; 1 keeps more trenches and rises from tectonics.
- **Turn up:** More leftover tectonic ocean shape.
- **Turn down:** Cleaner designed shelf profile.

## Easy

### `oceanLevel` — Ocean level

- **Default:** `1.0`
- **Range:** 0.5 … 1.5
- **In the planet:** Sea level used while generating the planet.
- **In Vintage Story:** Higher means more ocean and less land; lower means larger continents.
- **Turn up:** More ocean and coastline.
- **Turn down:** More landmass.

## Pack

### `blocksPerCell` — Blocks per cell

- **Default:** `32`
- **Range:** 8 … 128
- **In the planet:** Native-scale hint stored in the planet file header.
- **In Vintage Story:** Only matters if the mod uses native scale; Fit mode ignores it for world size.
- **Turn up:** Coarser native sampling.
- **Turn down:** Finer native sampling.

## Runtime

### `tempMinC` — Coldest climate °C

- **Default:** `-20.0`
- **Range:** -50.0 … 40.0
- **In the planet:** Cold end of the in-game °C window (Easy sets this from sun distance + Climate extremes).
- **In Vintage Story:** Cold end of the climate map.
- **Turn up:** Warmer coldest biomes.
- **Turn down:** Harsher polar climates.

### `tempMaxC` — Hottest climate °C

- **Default:** `40.0`
- **Range:** -20.0 … 60.0
- **In the planet:** Hot end of the in-game °C window (Easy sets this from sun distance + Climate extremes).
- **In Vintage Story:** Hot end of the climate map.
- **Turn up:** Hotter tropics.
- **Turn down:** Milder hot climates.

## Output

### `grayscaleHeightmap` — Write grayscale heightmap

- **Default:** `True`
- **In the planet:** Also writes a grayscale height preview next to the other images.
- **In Vintage Story:** Preview only; not used by the game.
- **Turn up:** Extra preview file.
- **Turn down:** Skip the grayscale image.

### `verbose` — Verbose generation

- **Default:** `True`
- **In the planet:** Writes detailed generation progress to the log.
- **In Vintage Story:** No gameplay effect.
- **Turn up:** More log detail.
- **Turn down:** Quieter log.
