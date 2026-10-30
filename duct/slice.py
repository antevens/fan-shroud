"""ElegooSlicer driver: writes print-ready project 3MFs and slices them headlessly.

The CLI resolves no profile `inherits`, so every vendor profile is flattened first. A project 3MF is
produced by loading the print-oriented STL of each body with its own filament; several bodies are merged
into one object with per-part filaments (`--assemble`), which keeps their relative placement.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

DEFAULT_SLICER_DIR = Path("/opt/elegooslicer")
PROFILE_SUBDIR = Path("resources") / "profiles" / "Elegoo"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"
MACHINE = "machine/ECC2/Elegoo Centauri Carbon 2 0.4 nozzle.json"
PROCESS = "process/ECC2/0.20mm Standard @Elegoo CC2 0.4 nozzle.json"
# Material name (as used in the config) -> vendor filament profile and an optional overrides file in configs/.
FILAMENT_PROFILES: dict[str, tuple[str, str | None]] = {
    "ABS": ("filament/ECC2/Elegoo ABS @ECC2.json", None),
    "TPU 95A": ("filament/ECC2/Elegoo TPU 95A @ECC2.json", None),
    "TPU 72D": ("filament/ECC2/Elegoo TPU 95A @ECC2.json", "filament_tpu72d.json"),
}
# Without a colour per filament the CLI counts one filament and drops every part on another one.
FILAMENT_COLOURS = {"ABS": "#5A5A5A", "TPU 95A": "#E07020", "TPU 72D": "#2B2B2B"}
PROCESS_OVERRIDES = {"rigid": "slicer_overrides.json", "tpu": "slicer_overrides_tpu.json"}
TIME_RE = re.compile(r"^; estimated printing time \(normal mode\) = (.+)$", re.MULTILINE)


class SlicerError(RuntimeError):
    pass


def slicer_dir() -> Path:
    return Path(os.environ.get("ELEGOOSLICER_DIR", DEFAULT_SLICER_DIR))


def slicer_available() -> bool:
    return shutil.which("elegooslicer") is not None and (slicer_dir() / PROFILE_SUBDIR).is_dir()


def profile_index(category_dir: Path) -> dict[str, Path]:
    """Map profile name to file for every JSON under a profile category directory."""
    index: dict[str, Path] = {}
    for path in category_dir.rglob("*.json"):
        try:
            name = json.loads(path.read_text()).get("name")
        except json.JSONDecodeError:
            continue
        if name:
            index.setdefault(name, path)
    return index


def flatten_profile(path: Path, index: dict[str, Path]) -> dict:
    """Profile with its whole `inherits` chain merged; the CLI does not resolve inheritance itself."""
    data = json.loads(path.read_text())
    parent_name = data.pop("inherits", None)
    if not parent_name:
        return data
    parent_path = index.get(parent_name)
    if parent_path is None:
        raise FileNotFoundError(f"{path.name} inherits unknown profile {parent_name!r}")
    merged = flatten_profile(parent_path, index)
    merged.update(data)
    return merged


def resolved_profile(profile_dir: Path, relative: str, work_dir: Path, overrides: dict | None = None,
                     suffix: str = "", tag: str | None = None) -> Path:
    """Write a flattened copy of a vendor profile (plus overrides) into work_dir and return it.

    Override values of None delete the key. `suffix` is appended to the profile name unless the overrides
    rename it; `tag` names the written file so several variants of one base profile can coexist.
    """
    path = profile_dir / relative
    category = path.relative_to(profile_dir).parts[0]
    data = flatten_profile(path, profile_index(profile_dir / category))
    if overrides:
        for key, value in overrides.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
    if suffix and not (overrides and "name" in overrides):
        data["name"] = data.get("name", category) + suffix
    target = work_dir / f"{category}_{tag or path.stem}.json"
    target.write_text(json.dumps(data, indent=2))
    return target


class Profiles:
    """Flattened machine, process and filament profiles for the Centauri Carbon 2, written on demand."""

    def __init__(self, work_dir: Path, profile_dir: Path | None = None, config_dir: Path = CONFIG_DIR):
        self.profile_dir = profile_dir or slicer_dir() / PROFILE_SUBDIR
        if not self.profile_dir.is_dir():
            raise SlicerError(f"ElegooSlicer profiles not found under {self.profile_dir}")
        self.work_dir = work_dir
        self.config_dir = config_dir
        self._cache: dict[str, Path] = {}

    def machine(self) -> Path:
        if "machine" not in self._cache:
            self._cache["machine"] = resolved_profile(self.profile_dir, MACHINE, self.work_dir)
        return self._cache["machine"]

    def process(self, kind: str) -> Path:
        """Process profile with the repo's overrides; `kind` is "rigid" or "tpu"."""
        key = f"process_{kind}"
        if key not in self._cache:
            overrides = json.loads((self.config_dir / PROCESS_OVERRIDES[kind]).read_text())
            suffix = " duct" if kind == "rigid" else f" duct {kind.upper()}"
            self._cache[key] = resolved_profile(self.profile_dir, PROCESS, self.work_dir, overrides, suffix, tag=key)
        return self._cache[key]

    def filament(self, material: str) -> Path:
        key = f"filament_{material}"
        if key not in self._cache:
            if material not in FILAMENT_PROFILES:
                raise SlicerError(f"no filament profile for material {material!r}; known: {', '.join(FILAMENT_PROFILES)}")
            base, extra = FILAMENT_PROFILES[material]
            overrides: dict = {"filament_colour": [FILAMENT_COLOURS[material]]}
            if extra:
                overrides.update(json.loads((self.config_dir / extra).read_text()))
            tag = "filament_" + re.sub(r"[^A-Za-z0-9]+", "_", material)
            self._cache[key] = resolved_profile(self.profile_dir, base, self.work_dir, overrides, tag=tag)
        return self._cache[key]


def read_result(run_dir: Path, exit_code: int) -> dict:
    result_path = run_dir / "result.json"
    if not result_path.exists():
        raise SlicerError(f"slicer produced no result.json (exit {exit_code})")
    return json.loads(result_path.read_text())


def rename_objects(source: Path, target: Path, object_name: str) -> None:
    """Copy a project 3MF, naming its object after the part and its parts after their STL stems."""
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "Metadata/model_settings.config":
                text = data.decode()
                text = text.replace('value="Assembly"', f'value="{object_name}"')
                text = re.sub(r'value="([^"]+)\.stl"', r'value="\1"', text)
                data = text.encode()
            dst.writestr(info, data)


def export_project(stls: list[Path], filaments: list[Path], machine: Path, process: Path, target: Path,
                   object_name: str) -> Path:
    """Have ElegooSlicer write a project 3MF: STL i on filament i, all merged into one object, placement kept."""
    if len(stls) != len(filaments):
        raise ValueError("one filament profile per STL body")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        command = [
            "elegooslicer",
            "--load-settings", f"{machine};{process}",
            "--load-filaments", ";".join(str(f) for f in filaments),
            "--load-filament-ids", ",".join(str(i + 1) for i in range(len(stls))),
            "--arrange", "0", "--orient", "0",
        ]
        if len(stls) > 1:
            command.append("--assemble")
        command += ["--export-3mf", target.name, "--outputdir", str(tmp_dir), *[str(s.resolve()) for s in stls]]
        run = subprocess.run(command, capture_output=True, text=True, timeout=600, cwd=tmp_dir)
        result = read_result(tmp_dir, run.returncode)
        if result.get("return_code", 1) != 0:
            raise SlicerError(f"{target.name}: {result.get('error_string', 'export failed')}")
        target.parent.mkdir(parents=True, exist_ok=True)
        rename_objects(tmp_dir / target.name, target, object_name)
    return target


def slice_project(project: Path, out_dir: Path) -> tuple[bool, str]:
    """Slice one project 3MF with its embedded settings; returns (ok, summary line)."""
    project = project.resolve()
    target = (out_dir / project.stem).resolve()
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    command = [
        "elegooslicer", "--slice", "0", "--export-3mf", f"{project.stem}.3mf", "--outputdir", str(target), str(project),
    ]
    run = subprocess.run(command, capture_output=True, text=True, timeout=1800, cwd=target)
    try:
        result = read_result(target, run.returncode)
    except SlicerError as error:
        return False, f"{project.stem}: {error}"
    if result.get("return_code", 1) != 0:
        return False, f"{project.stem}: {result.get('error_string', 'failed')}"
    warnings = [p.get("warning_message") for p in result.get("sliced_plates", []) if p.get("warning_message")]
    gcode = target / "plate_1.gcode"
    match = TIME_RE.search(gcode.read_text(errors="ignore")) if gcode.exists() else None
    summary = f"{project.stem}: {match.group(1) if match else 'no time estimate'}"
    if warnings:
        return False, summary + " | " + " | ".join(warnings)
    return True, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Slice the print-ready project 3MFs with ElegooSlicer.")
    parser.add_argument("--print-dir", default="print", help="directory holding the project .3mf files")
    parser.add_argument("--out", default="out", help="directory receiving out/sliced/<part>/")
    parser.add_argument("parts", nargs="*", help="part names to slice (default: every project in --print-dir and its coupons/)")
    args = parser.parse_args(argv)

    if not slicer_available():
        print("elegooslicer or its profiles not found", file=sys.stderr)
        return 1
    print_dir = Path(args.print_dir)
    candidates = sorted(print_dir.glob("*.3mf")) + sorted((print_dir / "coupons").glob("*.3mf"))
    if args.parts:
        by_name = {p.stem: p for p in candidates}
        missing = [n for n in args.parts if n not in by_name]
        if missing:
            print(f"not in {print_dir}: {', '.join(missing)}", file=sys.stderr)
            return 1
        candidates = [by_name[n] for n in args.parts]
    sliced_dir = Path(args.out) / "sliced"
    failed = False
    for project in candidates:
        ok, summary = slice_project(project, sliced_dir)
        print(("ok   " if ok else "FAIL ") + summary)
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
