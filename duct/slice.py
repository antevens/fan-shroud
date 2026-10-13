"""Slice the exported 3MF parts headlessly with ElegooSlicer and the Centauri Carbon 2 profiles."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_SLICER_DIR = Path.home() / "opt" / "elegooslicer-dl" / "squashfs-root"
PROFILE_SUBDIR = Path("resources") / "profiles" / "Elegoo"
MACHINE = "machine/ECC2/Elegoo Centauri Carbon 2 0.4 nozzle.json"
PROCESS = "process/ECC2/0.20mm Standard @Elegoo CC2 0.4 nozzle.json"
FILAMENT = "filament/ECC2/Elegoo ABS @ECC2.json"
FILAMENT_TPU = "filament/ECC2/Elegoo TPU 95A @ECC2.json"
TPU_PREFIXES = ("gasket", "grip", "coupon_grip")
TIME_RE = re.compile(r"^; estimated printing time \(normal mode\) = (.+)$", re.MULTILINE)


def slicer_dir() -> Path:
    return Path(os.environ.get("ELEGOOSLICER_DIR", DEFAULT_SLICER_DIR))


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


def resolved_profile(profile_dir: Path, relative: str, work_dir: Path, overrides: dict | None = None) -> Path:
    """Write a flattened copy of a vendor profile (plus overrides) into work_dir and return it."""
    path = profile_dir / relative
    category = path.relative_to(profile_dir).parts[0]
    data = flatten_profile(path, profile_index(profile_dir / category))
    if overrides:
        data.update(overrides)
        data["name"] = data.get("name", category) + " duct"
    target = work_dir / f"{category}_{path.stem}.json"
    target.write_text(json.dumps(data, indent=2))
    return target


def slice_part(part: Path, out_dir: Path, machine: Path, process: Path, filament: Path) -> tuple[bool, str]:
    """Run the slicer on one 3MF with flattened profiles; returns (ok, summary line)."""
    part = part.resolve()
    target = (out_dir / part.stem).resolve()
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    command = [
        "elegooslicer",
        "--load-settings", f"{machine};{process}",
        "--load-filaments", str(filament),
        "--slice", "0",
        "--export-3mf", f"{part.stem}.3mf",
        "--outputdir", str(target),
        str(part),
    ]
    run = subprocess.run(command, capture_output=True, text=True, timeout=1800, cwd=target)
    result_path = target / "result.json"
    if not result_path.exists():
        return False, f"{part.stem}: slicer produced no result.json (exit {run.returncode})"
    result = json.loads(result_path.read_text())
    if result.get("return_code", 1) != 0:
        return False, f"{part.stem}: {result.get('error_string', 'failed')}"
    warnings = [p.get("warning_message") for p in result.get("sliced_plates", []) if p.get("warning_message")]
    gcode = target / "plate_1.gcode"
    match = TIME_RE.search(gcode.read_text(errors="ignore")) if gcode.exists() else None
    summary = f"{part.stem}: {match.group(1) if match else 'no time estimate'}"
    if warnings:
        return False, summary + " | " + " | ".join(warnings)
    return True, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Slice exported parts with ElegooSlicer.")
    parser.add_argument("--out", default="out", help="directory holding the exported .3mf files")
    parser.add_argument("--overrides", default="configs/slicer_overrides.json", help="process overrides JSON")
    parser.add_argument("--filament", default=FILAMENT, help="filament profile relative to the Elegoo profile dir")
    parser.add_argument("--tpu-filament", default=FILAMENT_TPU, help="filament profile for gasket parts")
    parser.add_argument("parts", nargs="*", help="part names to slice (default: every .3mf in --out)")
    args = parser.parse_args(argv)

    profile_dir = slicer_dir() / PROFILE_SUBDIR
    if not profile_dir.is_dir():
        print(f"ElegooSlicer profiles not found under {profile_dir}", file=sys.stderr)
        return 1
    out_dir = Path(args.out)
    parts = [out_dir / f"{name}.3mf" for name in args.parts] or sorted(out_dir.glob("*.3mf"))
    sliced_dir = out_dir / "sliced"
    failed = False
    with tempfile.TemporaryDirectory() as work:
        work_dir = Path(work)
        machine = resolved_profile(profile_dir, MACHINE, work_dir)
        process = resolved_profile(profile_dir, PROCESS, work_dir, json.loads(Path(args.overrides).read_text()))
        rigid = resolved_profile(profile_dir, args.filament, work_dir)
        soft = resolved_profile(profile_dir, args.tpu_filament, work_dir)
        for part in parts:
            filament = soft if part.stem.startswith(TPU_PREFIXES) else rigid
            ok, summary = slice_part(part, sliced_dir, machine, process, filament)
            print(("ok   " if ok else "FAIL ") + summary)
            failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
