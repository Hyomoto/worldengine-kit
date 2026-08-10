# Quick start

## Requirements

- Windows 10/11 x64
- [Python 3.9+](https://www.python.org/downloads/) (3.12 recommended for freezes). During install, enable **Add python.exe to PATH**. Prefer the python.org installer over the Microsoft Store stub.

## First-time setup

1. Unzip / clone this kit to a folder you can write to.
2. Double-click **`setup.bat`** (or run it from a terminal). Wait until it finishes **and** prints `Setup complete`.
   - If setup fails, the window stays open with an **environment report**. Copy that text when asking for help; do not run PlanetKit yet.
3. Double-click **`PlanetKit.bat`**. It re-checks the environment before opening the UI. If checks fail, fix setup first.

You can also run `PlanetKit.bat doctor` any time to print the same diagnostic report.

## Generate a mod

1. On the **Easy** tab, set a world name and seed (or click **Randomize**).
2. Pick a map size (`1024` is a good first try; `2048` looks better but is slower).
3. Choose a style preset:
   - **balanced** — default shelf/peak tuning
   - **continental** — fewer plates, softer/wider shelves
   - **archipelago** — more plates, noisier coasts
4. Leave **Normalize temperature** checked unless you want a permanently cold (or hot) planet.
5. Click **Generate & pack mod**. Generation can take several minutes.
6. When finished, copy the zip path (**Copy zip path**) and place `*-worldengine.zip` in your Vintage Story `Mods` folder.

Previews (elevation / ocean / temperature) appear after a successful run. Intermediate files live under `output\<name>\`.

If Generate is disabled or PlanetKit refuses to start, the Log pane / console contains a copy/paste report (Python version, missing modules such as `numpy`, paths). Re-run **`setup.bat`** after installing a proper Python.

## CLI (optional)

```bat
PlanetKit.bat doctor
PlanetKit.bat generate --preset balanced --name myworld --seed 123 --width 1024 --height 1024
PlanetKit.bat presets
```

Use `--no-normalize-temperature` to keep absolute WorldEngine temperatures.

## After installing the mod

1. Place `*-worldengine.zip` in your Vintage Story `Mods` folder (remove any older `worldengine` zip/folder first).
2. Create a new world (or use a dedicated save). Check the server log for `[worldengine] Loaded` / `Rebound`.

**Planet path / ModConfig:** PlanetKit installs the planet as `assets/worldengine/planets/example.vsplanet` (same path the live mod uses). Vintage Story also keeps `ModConfig/worldengine.json`, which **overrides** the packaged asset config. If that file still points at a missing planet name, you get `Planet asset not found`. Either leave `PlanetAssetPath` as `worldengine:planets/example.vsplanet`, or delete `ModConfig/worldengine.json` once so the mod rewrites it from the zip.

PlanetKit still writes `planetAssetPath` and temperature range into the packaged assets config for fresh installs.
