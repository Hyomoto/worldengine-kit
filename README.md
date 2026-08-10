# WorldEngine Planet Kit

Generate Mindwerks WorldEngine planets, pack them to `.vsplanet`, and assemble a ready-to-drop **WorldEngine Planet** Vintage Story mod zip — without touching the developer build pipeline.

## Who this is for

Players and server hosts who want a custom climate/ocean/landform planet without reading WorldEngine CLI docs.

## Quick path

See [QUICKSTART.md](QUICKSTART.md).

`setup.bat` must finish with **Setup complete** (it runs an environment doctor). `PlanetKit.bat` refuses to start if required modules such as `numpy` are missing, and prints a copy/paste diagnostic report instead of failing later on Generate.

## Layout

| Path | Role |
|------|------|
| `PlanetKit.bat` | Launch GUI (no args) or CLI (`PlanetKit.bat generate ...`) |
| `setup.bat` | Create venv and install dependencies |
| `presets/` | Named generation styles (balanced / continental / archipelago) |
| `planet.json` | Last-used / default config |
| `docs/PARAMETERS.md` | What each knob actually changes in-game |
| `vendor/` | Vendored WorldEngine + packer (synced from the mod repo) |
| `mod-template/` | Prebuilt VS mod shell (DLL + assets) |
| `output/` | Generated worlds, previews, and mod zips |

## Maintainer sync

From a machine that has the sibling `worldengine` repo built (`dist/stage` with `worldengine.dll`):

```bat
python scripts\sync_from_dev.py
```

That refreshes a **trimmed** `vendor/worldengine` (package + install metadata + MIT license only), `vendor/packer`, and `mod-template` (sample `.vsplanet` files excluded).

## Clean / release packaging

Mod Portal uploads should be as small as possible. Local `venv/`, `dist/`, `build/`, and `output/` are never part of a release zip.

```bat
clean.bat                 # delete venv/dist/build/output/caches
pack_release.bat          # clean + zip lean kit -> release\worldengine-kit-YYYYMMDD.zip
```

The release zip is the **source kit** (users run `setup.bat`). For a frozen Windows build, run `setup.bat` then `scripts\build_pyinstaller.bat`, then zip only `dist\WorldEnginePlanetKit\` (exclude any `output\` folder inside it).

The playable VS mod alone is the tiny `*-worldengine.zip` produced by PlanetKit generate, or `mod-template/` after you inject a planet — not the whole kit.

## Defaults that matter

- **Normalize temperature is ON** in kit presets and Easy mode so VS can map the planet onto a full −20…40 °C spectrum (all biomes reachable). Turn it off only if you want a deliberately cold/hot absolute WE climate.
- The packed planet is always installed as **`example.vsplanet`** (world name only affects output/zip names). That matches the live mod path and typical `ModConfig/worldengine.json` `PlanetAssetPath`. Shipping under the generation name caused `Planet asset not found` when ModConfig still pointed at `example.vsplanet`.
- Generation knobs match the custom WorldEngine fork (shelf, coast noise, peaks). Ancient-map / HDF5 surfaces are not exposed.

## Frozen Windows build

After `setup.bat`:

```bat
scripts\build_pyinstaller.bat
```

Produces `dist\WorldEnginePlanetKit\` (onedir). Prefer Python **3.12 x64** for release freezes.

## License

PlanetKit’s own tooling is provided for use with the WorldEngine Planet Vintage Story mod.

**WorldEngine** (vendored under `vendor/worldengine/`) is included under the **MIT License**. Copyright (c) 2013-2014 Federico Tomassetti and Bret Curtis. See:

- [licenses/WORLDENGINE-MIT.txt](licenses/WORLDENGINE-MIT.txt)
- [THIRD_PARTY.md](THIRD_PARTY.md)
- `vendor/worldengine/LICENSE.txt`
