"""Card-clip shroud: a grooved side wall and bottom plate that ride on TPU grips pushed onto the cards.

Each card gets a soft U-channel grip over its top PCB edge. The ABS wall has one dovetail groove per
card (two undercut ribs and, for shorter cards, a pad as its floor); the grip's back carries the
matching key and slides in from the shroud's open bracket end, so the wall seals to every card edge
and holds its grips without screws. The top card's PCB is the roof of the top channel, so there is no
lid; a short stub only bridges from the tail end wall to that card's tail. The bottom plate closes the
lowest channel. A 60 mm fan bolts straight onto the tail end wall with standard fan screws driven from
inside (reached from the open motherboard side before the shroud goes on). At the bracket end one rib
per card runs along the wall to its edge and angles up to an ear on that card's PCI bracket tab, under
its screw; a ridge along each long edge of the rib stiffens it up to the screw head.
The shroud prints standing on its tail end wall, so the groove ribs and arms stand vertical.
"""

from __future__ import annotations

from build123d import Align, Box, Cylinder, Location, Part, Plane, Polyline, chamfer, extrude, make_face

from duct.outlet import box_between
from duct.params import Params

ON_BASE = (Align.CENTER, Align.CENTER, Align.MIN)


def edge_grip(params: Params, slot: int, length: float | None = None) -> Part:
    """U-channel grip for the card in `slot`, printed back-down with the channel opening up.

    The back carries the dovetail key, widest at the back face. Local frame: X along the card,
    Y across the PCB (grip width), Z = height (back at Z = 0).
    """
    length = params.grip_length(slot) if length is None else length
    body = Box(length, params.grip_outer_width, params.grip_height(slot), align=ON_BASE)
    key_half, neck_half = params.grip_key_width / 2, params.grip_outer_width / 2
    key = make_face(Polyline((-key_half, 0), (key_half, 0), (neck_half, params.dovetail_depth),
                             (-neck_half, params.dovetail_depth), close=True))
    body += extrude(Plane.YZ.offset(-length / 2) * key, amount=length)
    slot_cut = Box(length + 2, params.grip_slot_width, params.grip_engagement + 1, align=ON_BASE)
    return body - slot_cut.moved(Location((0, 0, params.grip_back(slot))))


def dovetail_groove(params: Params, slot: int, x0: float, x1: float) -> Part:
    """The groove of `slot` as a solid from x0 to x1, open past the rib tips."""
    face = make_face(Polyline(*params.pocket_groove_outline(slot), close=True))
    return extrude(Plane.YZ.offset(x0) * face, amount=x1 - x0)


def pockets(params: Params) -> Part:
    """Undercut ribs and floor pads on the wall's inner face forming one dovetail groove per card grip."""
    x0, x1 = params.shroud_x_min, params.shroud_x_max
    y_wall = params.shroud_wall_inner_y
    result: Part | None = None
    for slot in range(params.slot_positions_covered):
        g0, g1 = params.pocket_groove_z_range(slot)
        block = box_between(x0, x1, params.pocket_inner_y(slot), y_wall + 0.01, g0 - params.pocket_rib, g1 + params.pocket_rib)
        block -= dovetail_groove(params, slot, x0 - 1, x1 + 1)
        result = block if result is None else result + block
    assert result is not None
    return result


def tail_end_wall(params: Params) -> Part:
    """Plate across the shroud's tail with the fan opening and four fan screw clearance holes."""
    x0 = params.shroud_x_min
    x1 = x0 + params.tail_wall_thickness
    y0, y1 = params.tail_wall_y_range
    z0, z1 = params.tail_wall_z_range
    wall = box_between(x0, x1, y0, y1, z0, z1)
    along_x = (0, 90, 0)
    cy, cz = params.tail_fan_center_y_eff, params.tail_fan_center_z_eff
    length = params.tail_wall_thickness + 2
    wall -= Cylinder(params.tail_fan_opening / 2, length, rotation=along_x).moved(Location(((x0 + x1) / 2, cy, cz)))
    for y, z in params.tail_fan_hole_points():
        wall -= Cylinder(params.fan_screw_clearance / 2, length, rotation=along_x).moved(Location(((x0 + x1) / 2, y, z)))
    return wall


def bracket_mount(params: Params) -> Part:
    """One rib per covered slot: along the wall's outer face to the shroud's bracket-end edge, then angled
    up to an ear under that card's bracket screw, so the screws hold the cards and the shroud together.

    The ribs stand on the outside of the wall (outside the card zone), so the exhaust gap stays open between
    them and the space under each ear stays free for the metal bracket tab. A ridge stands on each long
    edge of the rib's upper side, from the wall to the ear and along it up to the screw head.
    """
    arm_face = make_face(Polyline(*params.bracket_arm_outline(), close=True))
    width = params.bracket_arm_width
    ridge_width = params.bracket_ridge_width
    ridge_face = None
    if params.bracket_ridge_height > 0:
        ridge_face = make_face(Polyline(*params.bracket_ridge_outline(), close=True))
    y_mid = params.bracket_tab_y + params.bracket_tab_thickness / 2
    result: Part | None = None
    for z in params.bracket_screw_points():
        arm = extrude(Plane.XY.offset(z - width / 2) * arm_face, amount=width)
        if ridge_face is not None:
            for z0 in (z - width / 2, z + width / 2 - ridge_width):
                arm += extrude(Plane.XY.offset(z0) * ridge_face, amount=ridge_width)
        hole = Cylinder(params.bracket_screw_clearance / 2, params.bracket_tab_thickness + 2, rotation=(90, 0, 0))
        arm -= hole.moved(Location((params.bracket_screw_x, y_mid, z)))
        result = arm if result is None else result + arm
    assert result is not None
    return result


def card_shroud(params: Params) -> Part:
    x0, x1 = params.shroud_x_min, params.shroud_x_max
    y_in, y_out = params.shroud_wall_inner_y, params.shroud_wall_outer_y
    y_min = params.cover_y_min
    wall = box_between(x0, x1, y_in, y_out, params.shroud_bottom_z, params.shroud_top_z)
    bottom = box_between(x0, x1, y_min, y_out, params.shroud_bottom_z, params.outlet_z_min)
    stub = box_between(x0, params.stub_x_max, y_min, y_out, params.outlet_z_max, params.outlet_z_max + params.wall_thickness)
    body = wall + bottom + stub + tail_end_wall(params) + pockets(params)
    inner = [
        e for e in body.edges()
        if abs(e.center().X - x1) < 1e-6 and (
            (abs(e.center().Y - y_in) < 1e-6 and params.outlet_z_min < e.center().Z < params.outlet_z_max)
            or (abs(e.center().Z - params.outlet_z_min) < 1e-6 and e.center().Y < y_in)
        )
    ]
    if inner and params.cover_edge_chamfer > 0:
        body = chamfer(inner, length=params.cover_edge_chamfer)
    return body + bracket_mount(params)
