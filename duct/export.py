"""Export helpers: STL and STEP in the duct frame, 3MF rotated into print orientation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from build123d import Axis, Compound, Location, Mesher, Part, export_step, export_stl

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

    def oriented(self, params: Params) -> Part:
        """Part rotated into print orientation, resting on Z = 0, centred on the bed."""
        shape = self.part
        for axis, angle in self.rotations:
            shape = shape.rotate(axis, angle)
        bb = shape.bounding_box()
        return shape.moved(
            Location((params.bed_x / 2 - bb.center().X, params.bed_y / 2 - bb.center().Y, -bb.min.Z))
        )


def export_part(print_part: PrintPart, params: Params, out_dir: Path) -> dict[str, Path]:
    """Write <name>.stl (duct frame) and <name>.3mf (print orientation)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stl_path = out_dir / f"{print_part.name}.stl"
    threemf_path = out_dir / f"{print_part.name}.3mf"
    export_stl(print_part.part, stl_path, tolerance=0.01, angular_tolerance=0.1)
    mesher = Mesher()
    mesher.add_shape(print_part.oriented(params), linear_deflection=0.01, angular_deflection=0.1,
                     part_number=print_part.name)
    mesher.write(threemf_path)
    return {"stl": stl_path, "3mf": threemf_path}


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
