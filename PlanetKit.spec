# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for WorldEngine Planet Kit (onedir, size-conscious)."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

KIT = Path(SPECPATH).resolve()

datas = [
    (str(KIT / "presets"), "presets"),
    (str(KIT / "mod-template"), "mod-template"),
    (str(KIT / "docs"), "docs"),
    (str(KIT / "licenses"), "licenses"),
    (str(KIT / "QUICKSTART.md"), "."),
    (str(KIT / "README.md"), "."),
    (str(KIT / "THIRD_PARTY.md"), "."),
    (str(KIT / "vendor" / "packer"), "vendor/packer"),
]

# Minimal WorldEngine fallback tree (runtime prefers frozen site-packages copy)
datas.append((str(KIT / "vendor" / "worldengine" / "worldengine"), "vendor/worldengine/worldengine"))
we_license = KIT / "vendor" / "worldengine" / "LICENSE.txt"
if we_license.is_file():
    datas.append((str(we_license), "vendor/worldengine"))

hiddenimports = [
    h
    for h in collect_submodules("worldengine")
    if ".tests" not in h and not h.endswith(".hdf5_serialization")
] + [
    "pack_vsplanet",
    "vsplanet",
    "World_pb2",
    "google.protobuf",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "PIL.PngImagePlugin",
    "platec",
    "noise",
    "png",
]

# Avoid collect_all(numpy/PIL) — it pulls tests and unused codecs (AVIF ~7MB, etc.).
excludes = [
    "matplotlib",
    "scipy",
    "h5py",
    "osgeo",
    "gdal",
    "setuptools",
    "pkg_resources",
    "numpy.tests",
    "numpy.f2py",
    "numpy.typing.tests",
    "PIL.AvifImagePlugin",
    "PIL.ImageQt",
    "PIL.ImageTk2",
    "tkinter.test",
]

a = Analysis(
    [str(KIT / "planetkit_app.py")],
    pathex=[str(KIT), str(KIT / "vendor" / "packer"), str(KIT / "vendor" / "worldengine")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PlanetKit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="WorldEnginePlanetKit",
)
