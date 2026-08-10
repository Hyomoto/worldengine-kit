"""Thin tkinter front end for PlanetKit."""

from __future__ import annotations

import os
import queue
import random
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from planetkit.doctor import format_report, run_doctor
from planetkit.pipeline import preview_paths, run_pipeline
from planetkit.schema import (
    FIELD_META,
    META_BY_KEY,
    PlanetConfig,
    apply_preset,
    default_config,
    list_presets,
    load_config,
    parse_field_value,
    save_config,
)


class PlanetKitApp(tk.Tk):
    def __init__(self, config_path: Path | None = None) -> None:
        super().__init__()
        self.title("WorldEngine Planet Kit")
        self.minsize(960, 640)
        self.config_path = config_path
        self.vars: dict[str, tk.Variable] = {}
        self._busy = False
        self._env_ok = True
        self._ui_q: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._help = tk.StringVar(value="Select a control to see what it changes.")

        try:
            self.cfg = load_config(config_path) if config_path else load_config()
        except Exception as exc:
            messagebox.showwarning("Config", f"Could not load planet.json ({exc}); using defaults.")
            self.cfg = default_config()

        self._build()
        self._load_cfg_into_vars(self.cfg)
        self._apply_doctor()
        self.after(100, self._poll_ui_queue)

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=8)
        outer.pack(fill=tk.BOTH, expand=True)

        nb = ttk.Notebook(outer)
        nb.pack(fill=tk.BOTH, expand=True)

        easy = ttk.Frame(nb, padding=8)
        adv = ttk.Frame(nb, padding=8)
        nb.add(easy, text="Easy")
        nb.add(adv, text="Advanced")

        self._build_easy(easy)
        self._build_advanced(adv)

        help_frame = ttk.LabelFrame(outer, text="What this does", padding=8)
        help_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(help_frame, textvariable=self._help, wraplength=900, justify=tk.LEFT).pack(
            anchor=tk.W
        )

        mid = ttk.Frame(outer)
        mid.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        log_frame = ttk.LabelFrame(mid, text="Log", padding=4)
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log = tk.Text(log_frame, height=14, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.configure(state=tk.DISABLED)

        preview_frame = ttk.LabelFrame(mid, text="Previews", padding=4)
        preview_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        self.preview_labels: dict[str, ttk.Label] = {}
        self._preview_images: list[Any] = []
        for key in ("elevation", "ocean", "temperature"):
            row = ttk.Frame(preview_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=key).pack(anchor=tk.W)
            lbl = ttk.Label(row, text="(none)")
            lbl.pack(anchor=tk.W)
            self.preview_labels[key] = lbl

        btns = ttk.Frame(outer)
        btns.pack(fill=tk.X, pady=(8, 0))
        self.gen_btn = ttk.Button(btns, text="Generate & pack mod", command=self._on_generate)
        self.gen_btn.pack(side=tk.LEFT)
        ttk.Button(btns, text="Save config", command=self._on_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Open output folder", command=self._on_open_output).pack(side=tk.LEFT)
        ttk.Button(btns, text="Copy zip path", command=self._on_copy_zip).pack(side=tk.LEFT, padx=6)

        self.status = tk.StringVar(value="Ready")
        ttk.Label(outer, textvariable=self.status).pack(anchor=tk.W, pady=(6, 0))
        self._last_zip: Path | None = None

    def _apply_doctor(self) -> None:
        result = run_doctor()
        report = format_report(result)
        self._append_log(report)
        self._env_ok = result.ok
        if result.ok:
            self.status.set("Ready")
            return
        self.gen_btn.configure(state=tk.DISABLED)
        self.status.set("Environment not ready — run setup.bat")
        messagebox.showerror(
            "Environment not ready",
            "PlanetKit is missing required modules or files.\n\n"
            "Re-run setup.bat and wait until it says Setup complete.\n"
            "The full diagnostic report is in the Log pane (copy/paste for bug reports).",
        )

    def _build_easy(self, parent: ttk.Frame) -> None:
        form = ttk.Frame(parent)
        form.pack(fill=tk.X)

        self._add_entry(form, "name", 0)
        self._add_seed_row(form, 1)
        self._add_size_row(form, 2)
        self._add_preset_row(form, 3)
        self._add_bool(form, "normalizeTemperature", 4)

        tip = (
            "Easy mode: pick a style, seed, and size. Normalize temperature stays ON so "
            "Vintage Story can see a full biome spectrum from the packed planet."
        )
        ttk.Label(parent, text=tip, wraplength=700, justify=tk.LEFT).pack(anchor=tk.W, pady=(12, 0))

    def _build_advanced(self, parent: ttk.Frame) -> None:
        canvas = tk.Canvas(parent, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        groups: dict[str, list] = {}
        for meta in FIELD_META:
            if meta.easy or meta.key in ("name", "seed", "width", "height", "preset", "normalizeTemperature"):
                continue
            groups.setdefault(meta.group, []).append(meta)

        row = 0
        for group, metas in groups.items():
            ttk.Label(inner, text=group.replace("_", " ").title(), font=("", 10, "bold")).grid(
                row=row, column=0, columnspan=3, sticky=tk.W, pady=(8, 2)
            )
            row += 1
            for meta in metas:
                if meta.kind == "bool":
                    self._add_bool(inner, meta.key, row, columns=True)
                elif meta.kind == "int":
                    self._add_spin(inner, meta.key, row, integer=True)
                elif meta.kind == "float":
                    self._add_spin(inner, meta.key, row, integer=False)
                else:
                    self._add_entry(inner, meta.key, row)
                row += 1

    def _bind_help(self, widget: tk.Widget, key: str) -> None:
        def show(_event=None) -> None:
            meta = META_BY_KEY.get(key)
            if not meta:
                return
            self._help.set(
                f"{meta.label}\n"
                f"In the planet: {meta.effect}\n"
                f"In Vintage Story: {meta.in_game}\n"
                f"Turn up: {meta.up}\n"
                f"Turn down: {meta.down}"
            )

        widget.bind("<FocusIn>", show)
        widget.bind("<Button-1>", show)

    def _add_entry(self, parent: ttk.Frame, key: str, row: int) -> None:
        meta = META_BY_KEY[key]
        ttk.Label(parent, text=meta.label).grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar()
        self.vars[key] = var
        ent = ttk.Entry(parent, textvariable=var, width=28)
        ent.grid(row=row, column=1, sticky=tk.W, pady=2)
        self._bind_help(ent, key)

    def _add_seed_row(self, parent: ttk.Frame, row: int) -> None:
        meta = META_BY_KEY["seed"]
        ttk.Label(parent, text=meta.label).grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar()
        self.vars["seed"] = var
        ent = ttk.Entry(parent, textvariable=var, width=20)
        ent.grid(row=row, column=1, sticky=tk.W, pady=2)
        self._bind_help(ent, "seed")
        ttk.Button(parent, text="Randomize", command=self._randomize_seed).grid(
            row=row, column=2, sticky=tk.W, padx=6
        )

    def _add_size_row(self, parent: ttk.Frame, row: int) -> None:
        ttk.Label(parent, text="Map size").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.size_choice = tk.StringVar(value="2048")
        box = ttk.Combobox(
            parent,
            textvariable=self.size_choice,
            values=("512", "1024", "2048"),
            state="readonly",
            width=10,
        )
        box.grid(row=row, column=1, sticky=tk.W, pady=2)
        self._bind_help(box, "width")
        box.bind("<<ComboboxSelected>>", self._on_size_chosen)

        wvar = tk.StringVar()
        hvar = tk.StringVar()
        self.vars["width"] = wvar
        self.vars["height"] = hvar

    def _add_preset_row(self, parent: ttk.Frame, row: int) -> None:
        meta = META_BY_KEY["preset"]
        ttk.Label(parent, text=meta.label).grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar()
        self.vars["preset"] = var
        box = ttk.Combobox(
            parent,
            textvariable=var,
            values=list_presets() or list(meta.choices),
            state="readonly",
            width=20,
        )
        box.grid(row=row, column=1, sticky=tk.W, pady=2)
        self._bind_help(box, "preset")
        box.bind("<<ComboboxSelected>>", self._on_preset_chosen)
        ttk.Button(parent, text="Apply preset", command=self._on_preset_chosen).grid(
            row=row, column=2, sticky=tk.W, padx=6
        )

    def _add_bool(self, parent: ttk.Frame, key: str, row: int, columns: bool = False) -> None:
        meta = META_BY_KEY[key]
        var = tk.BooleanVar()
        self.vars[key] = var
        cb = ttk.Checkbutton(parent, text=meta.label, variable=var)
        if columns:
            ttk.Label(parent, text=meta.label).grid(row=row, column=0, sticky=tk.W, pady=2)
            cb = ttk.Checkbutton(parent, variable=var)
            cb.grid(row=row, column=1, sticky=tk.W, pady=2)
        else:
            cb.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        self._bind_help(cb, key)

    def _add_spin(self, parent: ttk.Frame, key: str, row: int, *, integer: bool) -> None:
        meta = META_BY_KEY[key]
        ttk.Label(parent, text=meta.label).grid(row=row, column=0, sticky=tk.W, pady=2)
        if integer:
            var: tk.Variable = tk.IntVar()
            from_ = int(meta.min_value if meta.min_value is not None else 0)
            to = int(meta.max_value if meta.max_value is not None else 100)
            increment = int(meta.step if meta.step is not None else 1)
        else:
            var = tk.DoubleVar()
            from_ = float(meta.min_value if meta.min_value is not None else 0.0)
            to = float(meta.max_value if meta.max_value is not None else 1.0)
            increment = float(meta.step if meta.step is not None else 0.01)
        self.vars[key] = var
        spin = ttk.Spinbox(parent, textvariable=var, from_=from_, to=to, increment=increment, width=12)
        spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self._bind_help(spin, key)

    def _randomize_seed(self) -> None:
        self.vars["seed"].set(str(random.randint(0, 2_147_483_647)))

    def _on_size_chosen(self, _event=None) -> None:
        n = int(self.size_choice.get())
        self.vars["width"].set(str(n))
        self.vars["height"].set(str(n))

    def _on_preset_chosen(self, _event=None) -> None:
        name = self.vars["preset"].get()
        if not name:
            return
        try:
            # Preserve seed/name/size unless preset overwrites intentionally
            current = self._cfg_from_vars()
            seed, wname, width, height = current.seed, current.name, current.width, current.height
            cfg = apply_preset(default_config(), name)
            cfg.seed = seed
            cfg.name = wname
            cfg.width = width
            cfg.height = height
            cfg.preset = name
            self._load_cfg_into_vars(cfg)
            self._append_log(f"Applied preset '{name}'.")
        except Exception as exc:
            messagebox.showerror("Preset", str(exc))

    def _load_cfg_into_vars(self, cfg: PlanetConfig) -> None:
        data = cfg.to_dict()
        for key, var in self.vars.items():
            if key not in data:
                continue
            value = data[key]
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            else:
                var.set(value if not isinstance(value, float) else value)
        size = str(cfg.width)
        if size in ("512", "1024", "2048") and cfg.width == cfg.height:
            self.size_choice.set(size)
        self.vars["width"].set(str(cfg.width))
        self.vars["height"].set(str(cfg.height))
        self.vars["seed"].set(str(cfg.seed))

    def _cfg_from_vars(self) -> PlanetConfig:
        data = default_config().to_dict()
        for key, var in self.vars.items():
            raw = var.get()
            meta = META_BY_KEY.get(key)
            if meta is None:
                data[key] = raw
                continue
            data[key] = parse_field_value(meta, raw)
        # Prefer explicit width/height vars (easy size combobox writes both)
        data["width"] = parse_field_value(META_BY_KEY["width"], self.vars["width"].get())
        data["height"] = parse_field_value(META_BY_KEY["height"], self.vars["height"].get())
        data["outputDir"] = "output"
        return PlanetConfig.from_dict(data)

    def _append_log(self, msg: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _on_save(self) -> None:
        try:
            cfg = self._cfg_from_vars()
            path = self.config_path
            save_config(cfg, path)
            self._append_log(f"Saved config to {path or 'planet.json'}")
            self.status.set("Config saved")
        except Exception as exc:
            messagebox.showerror("Save", str(exc))

    def _on_open_output(self) -> None:
        from planetkit.pipeline import resolve_output_dir

        try:
            cfg = self._cfg_from_vars()
            path = resolve_output_dir(cfg)
            path.mkdir(parents=True, exist_ok=True)
            _open_path(path)
        except Exception as exc:
            messagebox.showerror("Output", str(exc))

    def _on_copy_zip(self) -> None:
        if not self._last_zip or not self._last_zip.is_file():
            messagebox.showinfo("Zip", "Generate a mod first.")
            return
        self.clipboard_clear()
        self.clipboard_append(str(self._last_zip))
        self.status.set("Zip path copied")

    def _poll_ui_queue(self) -> None:
        """Drain worker messages on the Tk main thread."""
        try:
            while True:
                kind, payload = self._ui_q.get_nowait()
                if kind == "log":
                    self._append_log(str(payload))
                elif kind == "done":
                    result, error = payload
                    self._on_generate_done(result, error)
        except queue.Empty:
            pass
        self.after(100, self._poll_ui_queue)

    def _on_generate(self) -> None:
        if self._busy:
            return
        if not self._env_ok:
            messagebox.showerror(
                "Environment not ready",
                "Required modules are missing. Re-run setup.bat first.\n"
                "See the Log pane for a copy/paste diagnostic report.",
            )
            return
        try:
            cfg = self._cfg_from_vars()
        except Exception as exc:
            messagebox.showerror("Config", str(exc))
            return

        self._busy = True
        self.gen_btn.configure(state=tk.DISABLED)
        self.status.set("Generating (this can take several minutes)...")
        self._append_log("--- Starting pipeline ---")

        def worker() -> None:
            try:
                result = run_pipeline(cfg, log=lambda m: self._ui_q.put(("log", m)))
                self._ui_q.put(("done", (result, None)))
            except Exception as exc:
                self._ui_q.put(("done", (None, exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_generate_done(self, result: dict | None, error: Exception | None) -> None:
        self._busy = False
        self.gen_btn.configure(state=tk.NORMAL)
        if error is not None:
            self.status.set("Failed")
            self._append_log(f"ERROR: {error}")
            messagebox.showerror("Generate", str(error))
            return
        assert result is not None
        self._last_zip = result.get("zip")
        self.status.set(f"Done: {self._last_zip}")
        self._append_log(f"Mod zip: {self._last_zip}")
        self._refresh_previews(result["work_dir"], self._cfg_from_vars())

    def _refresh_previews(self, work_dir: Path, cfg: PlanetConfig) -> None:
        try:
            from PIL import Image, ImageTk
        except ImportError:
            for key, lbl in self.preview_labels.items():
                path = preview_paths(cfg, work_dir).get(key)
                lbl.configure(text=str(path) if path and path.is_file() else "(no Pillow)")
            return

        self._preview_images.clear()
        paths = preview_paths(cfg, work_dir)
        for key, lbl in self.preview_labels.items():
            path = paths.get(key)
            if not path or not path.is_file():
                lbl.configure(image="", text="(missing)")
                continue
            img = Image.open(path)
            img.thumbnail((180, 180))
            photo = ImageTk.PhotoImage(img)
            self._preview_images.append(photo)
            lbl.configure(image=photo, text="")


def _open_path(path: Path) -> None:
    """Open a folder/file with the platform file manager."""
    target = str(path)
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target], start_new_session=True)
    else:
        subprocess.Popen(["xdg-open", target], start_new_session=True)


def run_gui(config_path: Path | None = None) -> None:
    app = PlanetKitApp(config_path)
    app.mainloop()


if __name__ == "__main__":
    run_gui()
