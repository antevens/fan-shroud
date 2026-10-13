"""80 mm fan flange: a square plate with the fan's 4-hole pattern and a square opening."""

from __future__ import annotations

from build123d import Align, Axis, Box, Cylinder, Location, Part, chamfer

from duct.params import Params

CENTERED = (Align.CENTER, Align.CENTER, Align.CENTER)


def fan_hole_centers(params: Params) -> list[tuple[float, float]]:
    """Hole centres in the flange plane (Y, Z) relative to the fan centre."""
    half = params.fan_hole_spacing / 2
    return [(-half, -half), (half, -half), (-half, half), (half, half)]


def fan_flange_local(params: Params) -> Part:
    """Flange in a local frame: plate in the YZ plane, fan face at X = 0, duct side at +X."""
    size = params.fan_flange_size
    thick = params.fan_flange_thickness
    opening = params.fan_inner
    plate = Box(thick, size, size, align=CENTERED).moved(Location((thick / 2, 0, 0)))
    if params.flange_chamfer > 0:
        duct_face = plate.faces().sort_by(Axis.X)[-1]
        plate = chamfer(duct_face.outer_wire().edges(), length=params.flange_chamfer)
    plate -= Box(thick * 3, opening, opening, align=CENTERED)
    for y, z in fan_hole_centers(params):
        hole = Cylinder(params.fan_hole_diameter / 2, thick * 3, rotation=(0, 90, 0))
        plate -= hole.moved(Location((0, y, z)))
    return plate


def fan_flange_coupon(params: Params) -> Part:
    """Printable test piece: the full flange, print flat, check the fan screws and frame fit."""
    part = fan_flange_local(params).rotate(Axis.Y, -90)
    bb = part.bounding_box()
    return part.moved(Location((-bb.center().X, -bb.center().Y, -bb.min.Z)))


def fan_flange(params: Params) -> Part:
    """Flange in the duct frame: fan face at fan_face_x, centred on the fan axis."""
    part = fan_flange_local(params)
    return part.moved(Location((params.fan_face_x, params.fan_center_y_eff, params.fan_center_z_eff)))
