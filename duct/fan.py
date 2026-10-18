"""80 mm fan flange: a square plate with the fan's 4-hole pattern and a square opening."""

from __future__ import annotations

from build123d import Align, Axis, Box, Cylinder, Location, Part, Polyline, chamfer, extrude, make_face

from duct.params import Params

CENTERED = (Align.CENTER, Align.CENTER, Align.CENTER)
ALONG_X = (0, 90, 0)


def fan_hole_centers(params: Params) -> list[tuple[float, float]]:
    """Hole centres in the flange plane (Y, Z) relative to the fan centre."""
    half = params.fan_hole_spacing / 2
    return [(-half, -half), (half, -half), (-half, half), (half, half)]


def fan_flange_local(params: Params, with_gussets: bool = True) -> Part:
    """Flange in a local frame: plate in the YZ plane, fan face at X = 0, duct side at +X.

    The duct build adds the gussets separately, trimmed to the duct's outer envelope.
    """
    size = params.fan_flange_size
    thick = params.fan_flange_thickness
    opening = params.fan_inner
    plate = Box(thick, size, size, align=CENTERED).moved(Location((thick / 2, 0, 0)))
    if params.flange_chamfer > 0:
        duct_face = plate.faces().sort_by(Axis.X)[-1]
        plate = chamfer(duct_face.outer_wire().edges(), length=params.flange_chamfer)
    plate -= Box(thick * 3, opening, opening, align=CENTERED)
    # The opening's four corners stay filled (outside the blade sweep). Fan screws come from the duct
    # side through a clearance hole in each pad, the head seated fan_screw_seat from the fan face. Behind
    # each pad a 45 deg gusset, fused to both corner walls, lets the pad print outlet-face-down.
    pad = params.fan_corner_pad
    half = opening / 2
    for y, z in fan_hole_centers(params):
        sy, sz = (1 if y > 0 else -1), (1 if z > 0 else -1)
        yc, zc = sy * (half - pad / 2), sz * (half - pad / 2)
        plate += Box(thick, pad, pad, align=CENTERED).moved(Location((thick / 2, yc, zc)))
        if with_gussets:
            plate += corner_gusset(thick, half, pad, params.fan_gusset_tip, sy, sz)
    return plate - screw_holes(params, thick + params.fan_corner_pad)


def axial_cylinder(radius: float, x0: float, x1: float, y: float, z: float) -> Part:
    return Cylinder(radius, x1 - x0, rotation=ALONG_X).moved(Location(((x0 + x1) / 2, y, z)))


def screw_holes(params: Params, x_end: float) -> Part:
    """Local frame: clearance hole through the seat, head bore from the seat back to x_end, per corner."""
    seat = params.fan_screw_seat
    result: Part | None = None
    for y, z in fan_hole_centers(params):
        hole = axial_cylinder(params.fan_screw_clearance / 2, -1, seat + 0.01, y, z)
        hole += axial_cylinder(params.fan_screw_head_clearance / 2, seat, x_end, y, z)
        result = hole if result is None else result + hole
    assert result is not None
    return result


def fan_screw_tubes(params: Params) -> Part:
    """Duct frame: a solid round boss on each screw axis from the flange back to the outlet face.

    The boss stays whole even where it leaves the duct's walls, so every head bore (cut later by
    fan_screw_bores) keeps fan_screw_tube_wall all round and stays sealed from the air passage. It
    remains inside the flange outline, so it adds nothing to the fan end's envelope.
    """
    radius = params.fan_screw_head_clearance / 2 + params.fan_screw_tube_wall
    x_end = params.outlet_x - params.fan_face_x
    result: Part | None = None
    for y, z in fan_hole_centers(params):
        # From the seat, so the flange's back-edge chamfer does not thin the tube wall.
        tube = axial_cylinder(radius, params.fan_screw_seat, x_end, y, z)
        result = tube if result is None else result + tube
    assert result is not None
    return result.moved(flange_location(params))


def fan_screw_bores(params: Params) -> Part:
    """Duct frame: the screw holes with head bores running out through the outlet face for the driver."""
    return screw_holes(params, params.outlet_x - params.fan_face_x + 1).moved(flange_location(params))


def corner_gusset(x0: float, half: float, pad: float, tip: float, sy: int, sz: int) -> Part:
    """Block behind a corner pad whose two inner faces slope at 45 deg down to a tip x tip end."""
    length = pad - tip
    yc, zc = sy * (half - pad / 2), sz * (half - pad / 2)
    block = Box(length, pad, pad, align=CENTERED).moved(Location((x0 + length / 2, yc, zc)))
    # Cut away everything closer to the opening centre than the 45 deg plane, in Y and in Z.
    y_in, y_out = sy * (half - pad), sy * half
    tri_y = Polyline((x0, y_in, 0), (x0 + length, y_out - sy * tip, 0), (x0 + length, y_in, 0), close=True)
    cut_y = extrude(make_face(tri_y), amount=pad, both=True).moved(Location((0, 0, zc)))
    z_in, z_out = sz * (half - pad), sz * half
    tri_z = Polyline((x0, 0, z_in), (x0 + length, 0, z_out - sz * tip), (x0 + length, 0, z_in), close=True)
    cut_z = extrude(make_face(tri_z), amount=pad, both=True).moved(Location((0, yc, 0)))
    return block - cut_y - cut_z


def fan_flange_coupon(params: Params) -> Part:
    """Printable test piece: the full flange, print flat, check the fan screws and frame fit."""
    part = fan_flange_local(params).rotate(Axis.Y, -90)
    bb = part.bounding_box()
    return part.moved(Location((-bb.center().X, -bb.center().Y, -bb.min.Z)))


def flange_location(params: Params) -> Location:
    return Location((params.fan_face_x, params.fan_center_y_eff, params.fan_center_z_eff))


def fan_flange(params: Params) -> Part:
    """Flange in the duct frame without gussets: fan face at fan_face_x, centred on the fan axis."""
    return fan_flange_local(params, with_gussets=False).moved(flange_location(params))


def fan_gussets(params: Params) -> Part:
    """The four corner gussets in the duct frame, untrimmed; intersect with the outer body before use."""
    thick = params.fan_flange_thickness
    half = params.fan_inner / 2
    result: Part | None = None
    for y, z in fan_hole_centers(params):
        sy, sz = (1 if y > 0 else -1), (1 if z > 0 else -1)
        gusset = corner_gusset(thick, half, params.fan_corner_pad, params.fan_gusset_tip, sy, sz)
        result = gusset if result is None else result + gusset
    assert result is not None
    return result.moved(flange_location(params))
