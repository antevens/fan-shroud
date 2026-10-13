"""Export helpers: STL and STEP in the duct frame, per-body STLs rotated into print orientation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from build123d import Axis, Compound, Location, Part, export_step, export_stl

from duct.params import Params


@dataclass
class PrintPart:
    """A part with its print orientation and metadata for PRINTING.md."""

    name: str
    part: Part
    quantity: int
    material: str
    orientation: str
    rotations: tuple[tuple[Axis, float], ...]
    notes: str = ""
    bodies: dict[str, Part] | None = None
    body_materials: dict[str, str] | None = None

    def filament_bodies(self) -> list[tuple[str, Part, str]]:
        """(object name, shape, material) per printed body; several when the part is multi-material."""
        if self.bodies:
            materials = self.body_materials or {}
            return [(f"{self.name}_{body}", shape, materials.get(body, self.material)) for body, shape in self.bodies.items()]
        return [(self.name, self.part, self.material)]

    def print_location(self, params: Params) -> Location:
        """Translation that puts the rotated part on Z = 0, centred on the bed."""
        shape = self.part
        for axis, angle in self.rotations:
            shape = shape.rotate(axis, angle)
        bb = shape.bounding_box()
        return Location((params.bed_x / 2 - bb.center().X, params.bed_y / 2 - bb.center().Y, -bb.min.Z))

    def orient(self, shape: Part, params: Params) -> Part:
        for axis, angle in self.rotations:
            shape = shape.rotate(axis, angle)
        return shape.moved(self.print_location(params))

    def oriented(self, params: Params) -> Part:
        """Part rotated into print orientation, resting on Z = 0, centred on the bed."""
        return self.orient(self.part, params)


def export_part(print_part: PrintPart, params: Params, out_dir: Path) -> dict:
    """Write <name>.stl in the duct frame and oriented/<body>.stl per body in print orientation on the bed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stl_path = out_dir / f"{print_part.name}.stl"
    export_stl(print_part.part, stl_path, tolerance=0.01, angular_tolerance=0.1)
    oriented_dir = out_dir / "oriented"
    oriented_dir.mkdir(exist_ok=True)
    oriented: list[Path] = []
    for body_name, shape, _ in print_part.filament_bodies():
        path = oriented_dir / f"{body_name}.stl"
        export_stl(print_part.orient(shape, params), path, tolerance=0.01, angular_tolerance=0.1)
        oriented.append(path)
    return {"stl": stl_path, "oriented": oriented}


def export_assembly(parts: dict[str, Part], instances: dict[str, list[Location]], out_dir: Path) -> Path:
    """Write every part, placed at each of its instance locations in the duct frame, to one STEP file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    children = []
    for name, part in parts.items():
        for index, location in enumerate(instances.get(name, [Location()])):
            placed = Part(part.moved(location).wrapped)
            placed.label = name if index == 0 else f"{name}_{index + 1}"
            children.append(placed)
    assembly = Compound(children=children)
    assembly.label = "pcie_fan_duct"
    path = out_dir / "assembly.step"
    export_step(assembly, path)
    return path
