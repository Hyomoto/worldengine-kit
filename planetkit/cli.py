"""CLI entry for WorldEngine Planet Kit."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from planetkit.doctor import ensure_ready, format_report, run_doctor
from planetkit.pipeline import run_pipeline
from planetkit.schema import (
    apply_preset,
    default_config,
    list_presets,
    load_config,
    parameters_markdown,
    save_config,
)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="planetkit",
        description="Generate a WorldEngine planet and assemble a Vintage Story mod zip.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="Run generate -> pack -> assemble")
    p_gen.add_argument("-c", "--config", type=Path, help="planet.json path")
    p_gen.add_argument("--preset", help="Apply preset before generate")
    p_gen.add_argument("--name", help="Override world name")
    p_gen.add_argument("--seed", type=int, help="Override seed")
    p_gen.add_argument("--width", type=int, help="Override width")
    p_gen.add_argument("--height", type=int, help="Override height")
    p_gen.add_argument(
        "--no-normalize-temperature",
        action="store_true",
        help="Keep absolute WE temperatures (cold planets stay cold)",
    )
    p_gen.add_argument("--skip-assemble", action="store_true", help="Only generate and pack")

    p_gui = sub.add_parser("gui", help="Open the PlanetKit window")
    p_gui.add_argument("-c", "--config", type=Path, help="planet.json path")

    sub.add_parser("presets", help="List available presets")
    sub.add_parser("doctor", help="Validate Python environment and required modules")

    p_docs = sub.add_parser("write-params-doc", help="Write docs/PARAMETERS.md from schema")
    p_docs.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output markdown path",
    )

    p_init = sub.add_parser("init-config", help="Write default planet.json")
    p_init.add_argument("-o", "--output", type=Path, default=None)
    p_init.add_argument("--preset", default="balanced")

    return ap


def _require_env(*, force: bool = False) -> int | None:
    """Return exit code if environment is not ready; None if ok."""
    if not force and os.environ.get("PLANETKIT_DOCTOR_OK") == "1":
        return None
    result = run_doctor()
    print(format_report(result))
    if not result.ok:
        return 1
    return None


def cmd_generate(args: argparse.Namespace) -> int:
    bad = _require_env(force=True)
    if bad is not None:
        return bad

    cfg = load_config(args.config) if args.config else load_config()
    if args.preset:
        cfg = apply_preset(cfg, args.preset)
    if args.name:
        cfg.name = args.name
    if args.seed is not None:
        cfg.seed = args.seed
    if args.width is not None:
        cfg.width = args.width
    if args.height is not None:
        cfg.height = args.height
    if args.no_normalize_temperature:
        cfg.normalizeTemperature = False

    result = run_pipeline(cfg, skip_assemble=bool(args.skip_assemble))
    print("Artifacts:")
    for key, path in result.items():
        print(f"  {key}: {path}")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    bad = _require_env(force=False)
    if bad is not None:
        return bad
    from planetkit.gui import run_gui

    run_gui(args.config)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    # Bare launch with no args -> GUI (double-click / PlanetKit.bat)
    if not argv:
        bad = _require_env(force=False)
        if bad is not None:
            return bad
        from planetkit.gui import run_gui

        run_gui()
        return 0

    ap = build_parser()
    args = ap.parse_args(argv)

    if args.command == "doctor":
        result = ensure_ready(exit_on_fail=False)
        return 0 if result.ok else 1
    if args.command == "generate":
        return cmd_generate(args)
    if args.command == "gui":
        return cmd_gui(args)
    if args.command == "presets":
        for name in list_presets():
            print(name)
        return 0
    if args.command == "write-params-doc":
        from planetkit.paths import user_root

        out = args.output or (user_root() / "docs" / "PARAMETERS.md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(parameters_markdown(), encoding="utf-8")
        print(f"Wrote {out}")
        return 0
    if args.command == "init-config":
        from planetkit.paths import user_root

        cfg = apply_preset(default_config(), args.preset)
        out = args.output or (user_root() / "planet.json")
        save_config(cfg, out)
        print(f"Wrote {out}")
        return 0

    ap.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
