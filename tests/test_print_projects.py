"""The print set must be written by ElegooSlicer itself: project 3MFs with presets and per-part filaments."""

from __future__ import annotations

import json
import re
import tempfile
import zipfile
from pathlib import Path

import pytest

from duct.build import build_parts, write_project
from duct.export import PrintPart, export_part
from duct.params import load_params
from duct.slice import Profiles, slicer_available

pytestmark = pytest.mark.skipif(not slicer_available(), reason="ElegooSlicer is not installed")

CONFIG = Path(__file__).resolve().parent.parent / "configs" / "default.toml"
PROJECT_PARTS = ("shroud", "grip_slot1")


@pytest.fixture(scope="module")
def projects(tmp_path_factory) -> tuple[object, dict[str, tuple[PrintPart, zipfile.ZipFile]]]:
    params = load_params(str(CONFIG))
    parts = build_parts(params)
    out_dir = tmp_path_factory.mktemp("projects")
    result = {}
    with tempfile.TemporaryDirectory() as work:
        profiles = Profiles(Path(work))
        for name in PROJECT_PARTS:
            item = parts[name]
            written = export_part(item, params, out_dir)
            path = write_project(item, written["oriented"], out_dir, profiles)
            result[name] = (item, zipfile.ZipFile(path))
    return params, result


def model_text(archive: zipfile.ZipFile) -> str:
    return archive.read("3D/3dmodel.model").decode()


def settings(archive: zipfile.ZipFile) -> dict:
    return json.loads(archive.read("Metadata/project_settings.config"))


def part_extruders(archive: zipfile.ZipFile) -> dict[str, int]:
    """Part name -> filament number from the model settings (whole-object entries when there are no parts)."""
    text = archive.read("Metadata/model_settings.config").decode()
    found: dict[str, int] = {}
    blocks = re.findall(r"<part [^>]*>(.*?)</part>", text, flags=re.S)
    blocks += [body.split("<part", 1)[0] for body in re.findall(r"<object [^>]*>(.*?)</object>", text, flags=re.S)]
    for block in blocks:
        name = re.search(r'key="name" value="([^"]*)"', block)
        extruder = re.search(r'key="extruder" value="(\d+)"', block)
        if name and extruder:
            found[name.group(1)] = int(extruder.group(1))
    return found


def placed_bounds(archive: zipfile.ZipFile) -> list[tuple[float, ...]]:
    """Bounding box of every mesh after its component and build-item transforms (translations only)."""
    text = model_text(archive)
    boxes = []
    for object_id, body in re.findall(r'<object id="(\d+)"[^>]*>(.*?)</object>', text, flags=re.S):
        item = re.search(rf'<item objectid="{object_id}"[^>]*transform="([^"]*)"', text)
        if item is None:
            continue
        item_t = [float(v) for v in item.group(1).split()]
        assert item_t[:9] == [1, 0, 0, 0, 1, 0, 0, 0, 1], "build item must not rotate the part"
        for path, mesh_id, transform in re.findall(r'<component p:path="([^"]*)" objectid="(\d+)"[^>]*transform="([^"]*)"', body):
            comp_t = [float(v) for v in transform.split()]
            assert comp_t[:9] == [1, 0, 0, 0, 1, 0, 0, 0, 1], "component must not rotate the body"
            model = archive.read(path.lstrip("/")).decode()
            mesh = re.search(rf'<object id="{mesh_id}"[^>]*>(.*?)</object>', model, flags=re.S).group(1)
            verts = [tuple(float(v) for v in m) for m in re.findall(r'<vertex x="([-\d.e+]+)" y="([-\d.e+]+)" z="([-\d.e+]+)"', mesh)]
            offset = [comp_t[9 + i] + item_t[9 + i] for i in range(3)]
            lo = [min(v[i] for v in verts) + offset[i] for i in range(3)]
            hi = [max(v[i] for v in verts) + offset[i] for i in range(3)]
            boxes.append((*lo, *hi))
    return boxes


def test_projects_are_elegooslicer_files(projects):
    _, result = projects
    for name, (_, archive) in result.items():
        application = re.search(r'<metadata name="Application">([^<]*)', model_text(archive))
        assert application and application.group(1).startswith("ElegooSlicer"), name
        assert "Metadata/project_settings.config" in archive.namelist()
        assert settings(archive)["printer_settings_id"] == "Elegoo Centauri Carbon 2 0.4 nozzle"


def test_rigid_project_settings(projects):
    params, result = projects
    _, archive = result["shroud"]
    config = settings(archive)
    assert config["filament_settings_id"] == [f"Elegoo {params.material} @ECC2"]
    assert config["wall_loops"] == "4" and config["sparse_infill_density"] == "20%" and config["enable_support"] == "0"
    assert part_extruders(archive) == {"shroud": 1}
    # The CLI exports Cool Plate (30 C bed) unless told otherwise; ABS must start on the 90 C textured plate.
    assert config["curr_bed_type"] == "Textured PEI Plate"
    assert config["textured_plate_temp"] == ["90"] and config["textured_plate_temp_initial_layer"] == ["90"]


def test_grip_project_is_one_tpu_body(projects):
    params, result = projects
    _, archive = result["grip_slot1"]
    config = settings(archive)
    assert config["filament_settings_id"] == [f"Elegoo {params.grip_material} @ECC2"]
    assert config["sparse_infill_density"] == "100%" and config["brim_type"] == "no_brim"
    assert config["curr_bed_type"] == "Textured PEI Plate"
    assert config["textured_plate_temp"] == ["35"], "TPU 95A at 35 C"
    assert part_extruders(archive) == {"grip_slot1": 1}


def test_grip_keeps_its_print_placement(projects):
    params, result = projects
    item, archive = result["grip_slot1"]
    bb = item.oriented(params).bounding_box()
    placed = placed_bounds(archive)
    assert len(placed) == 1
    assert placed[0] == pytest.approx((bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z), abs=0.05)
